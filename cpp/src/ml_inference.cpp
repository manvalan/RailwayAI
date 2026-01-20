#include "ml_inference.h"
#include <iostream>

#ifdef USE_LIBTORCH
#include <torch/script.h>
#endif

namespace railway {

struct MLInferenceEngine::Impl {
#ifdef USE_LIBTORCH
    torch::jit::script::Module module;
#endif
};

MLInferenceEngine::MLInferenceEngine() 
    : pImpl(std::make_unique<Impl>()), model_loaded_(false) {
}

MLInferenceEngine::~MLInferenceEngine() = default;

bool MLInferenceEngine::load(const std::string& model_path) {
#ifdef USE_LIBTORCH
    try {
        pImpl->module = torch::jit::load(model_path);
        model_loaded_ = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error loading ML model: " << e.what() << std::endl;
        model_loaded_ = false;
        return false;
    }
#else
    std::cerr << "LibTorch support not compiled. Cannot load model: " << model_path << std::endl;
    return false;
#endif
}

std::vector<ScheduleAdjustment> MLInferenceEngine::predict_adjustments(
    const NetworkState& state,
    const std::vector<Conflict>& conflicts) {
    
    std::vector<ScheduleAdjustment> adjustments;
    if (!model_loaded_) return adjustments;

#ifdef USE_LIBTORCH
    try {
        // 1. Convert state and conflicts to Tensors
        // Formato: [Batch=1, NumConflicts, Features=10]
        int num_conflicts = static_cast<int>(conflicts.size());
        if (num_conflicts == 0) return adjustments;

        torch::Tensor input_tensor = torch::zeros({1, num_conflicts, 10});
        
        for (int i = 0; i < num_conflicts; ++i) {
            const auto& c = conflicts[i];
            // Feature mapping: 
            // 0: train1_id, 1: train2_id, 2: track_id, 3: severity
            // 4: collision_time, 5: train1_velocity, 6: train2_velocity, etc.
            input_tensor[0][i][0] = c.train1_id;
            input_tensor[0][i][1] = c.train2_id;
            input_tensor[0][i][2] = c.track_id;
            input_tensor[0][i][3] = c.severity / 10.0f;
            input_tensor[0][i][4] = c.estimated_collision_time_minutes / 60.0f;
        }

        // 2. Perform inference
        std::vector<torch::jit::IValue> inputs;
        inputs.push_back(input_tensor);
        
        auto output = pImpl->module.forward(inputs).toTensor();
        // Output format: [1, num_conflicts, 1] (time adjustment index or value)

        // 3. Post-process output to ScheduleAdjustment list
        for (int i = 0; i < num_conflicts; ++i) {
            float pred = output[0][i][0].item<float>();
            
            ScheduleAdjustment adj;
            adj.train_id = conflicts[i].train1_id;
            adj.time_adjustment_minutes = pred; // Il modello predice il ritardo necessario
            adj.confidence = 0.90;
            adj.reason = "ML optimized resolution";
            adjustments.push_back(adj);
        }
        
    } catch (const std::exception& e) {
        std::cerr << "Inference error: " << e.what() << std::endl;
    }
#endif

    return adjustments;
}

} // namespace railway
