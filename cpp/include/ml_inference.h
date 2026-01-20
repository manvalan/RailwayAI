#pragma once

#include "railway_scheduler.h"
#include <string>
#include <memory>
#include <vector>

namespace railway {

/**
 * @brief Engine for running ML inference using LibTorch (TorchScript)
 */
class MLInferenceEngine {
public:
    MLInferenceEngine();
    ~MLInferenceEngine();

    /**
     * @brief Load a TorchScript model from file
     * @param model_path Path to the .pt or .pth TorchScript file
     * @return true if loaded successfully
     */
    bool load(const std::string& model_path);

    /**
     * @brief Predict schedule adjustments for a set of conflicts
     * @param state Current network state
     * @param conflicts List of detected conflicts
     * @return List of suggested adjustments
     */
    std::vector<ScheduleAdjustment> predict_adjustments(
        const NetworkState& state,
        const std::vector<Conflict>& conflicts);

    /**
     * @brief Check if model is loaded and ready
     */
    bool is_ready() const { return model_loaded_; }

private:
    struct Impl;
    std::unique_ptr<Impl> pImpl;
    bool model_loaded_;
};

} // namespace railway
