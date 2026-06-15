#pragma once

#include <cstdint>

#include "vision_input.h"


namespace pet {

enum class PetState : uint8_t {
    Standby,
    Attentive,
    Listening,
    Thinking,
    Talking,
    NoVision,
};

enum class PetExpression : uint8_t {
    Neutral,
    Curious,
    Listening,
    Thinking,
    Talking,
    Sleepy,
};

struct PetSnapshot {
    PetState state = PetState::Standby;
    PetExpression expression = PetExpression::Sleepy;
    int16_t eyeTargetX = 0;
    int16_t eyeTargetY = 0;
};

class PetStateMachine {
public:
    void handleVisionEvent(const vision::VisionEvent& event);
    const PetSnapshot& snapshot() const { return snapshot_; }

private:
    bool isFacing(const vision::FaceObservation& face) const;
    void centerEyes();
    void setEyeTargetFromFace(const vision::FaceObservation& face);
    void enterStandby(PetExpression expression);

    PetSnapshot snapshot_ = {};
};

}  // namespace pet
