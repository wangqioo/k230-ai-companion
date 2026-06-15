#include "pet_state_machine.h"


namespace pet {
namespace {

constexpr int16_t kFacingYawLimitCentidegrees = 3000;
constexpr int16_t kFacingPitchLimitCentidegrees = 3000;
constexpr int16_t kEyeTargetXLimit = 800;
constexpr int16_t kEyeTargetYLimit = 600;

int16_t clampInt16(int32_t value, int16_t minimum, int16_t maximum) {
    if (value < minimum) {
        return minimum;
    }
    if (value > maximum) {
        return maximum;
    }
    return static_cast<int16_t>(value);
}

int16_t absInt16(int16_t value) {
    return value < 0 ? static_cast<int16_t>(-value) : value;
}

}  // namespace

bool PetStateMachine::isFacing(const vision::FaceObservation& face) const {
    return absInt16(face.yawCentidegrees) <= kFacingYawLimitCentidegrees &&
           absInt16(face.pitchCentidegrees) <= kFacingPitchLimitCentidegrees;
}

void PetStateMachine::centerEyes() {
    snapshot_.eyeTargetX = 0;
    snapshot_.eyeTargetY = 0;
}

void PetStateMachine::setEyeTargetFromFace(const vision::FaceObservation& face) {
    snapshot_.eyeTargetX = clampInt16(
        static_cast<int32_t>(face.centerX) * kEyeTargetXLimit / 1000,
        -kEyeTargetXLimit,
        kEyeTargetXLimit
    );
    snapshot_.eyeTargetY = clampInt16(
        static_cast<int32_t>(face.centerY) * kEyeTargetYLimit / 1000,
        -kEyeTargetYLimit,
        kEyeTargetYLimit
    );
}

void PetStateMachine::enterStandby(PetExpression expression) {
    snapshot_.state = PetState::Standby;
    snapshot_.expression = expression;
    centerEyes();
}

void PetStateMachine::handleVisionEvent(const vision::VisionEvent& event) {
    switch (event.type) {
        case vision::VisionEventType::FaceVisible:
            if (isFacing(event.face)) {
                snapshot_.state = PetState::Attentive;
                snapshot_.expression = PetExpression::Curious;
                setEyeTargetFromFace(event.face);
            } else {
                enterStandby(PetExpression::Neutral);
            }
            break;

        case vision::VisionEventType::FaceLost:
            enterStandby(PetExpression::Neutral);
            break;

        case vision::VisionEventType::VisionTimeout:
            snapshot_.state = PetState::NoVision;
            snapshot_.expression = PetExpression::Sleepy;
            centerEyes();
            break;

        case vision::VisionEventType::VisionAvailable:
            if (snapshot_.state == PetState::NoVision) {
                enterStandby(PetExpression::Sleepy);
            }
            break;

        default:
            break;
    }
}

}  // namespace pet
