#include <cassert>

#include "../../esp32/vision_receiver/pet_state_machine.h"


static vision::VisionEvent faceEvent(
    int16_t centerX,
    int16_t centerY,
    int16_t yawCentidegrees,
    int16_t pitchCentidegrees = 0
) {
    vision::VisionEvent event;
    event.type = vision::VisionEventType::FaceVisible;
    event.face.centerX = centerX;
    event.face.centerY = centerY;
    event.face.yawCentidegrees = yawCentidegrees;
    event.face.pitchCentidegrees = pitchCentidegrees;
    event.face.confidence = 90;
    return event;
}


int main() {
    pet::PetStateMachine machine;

    assert(machine.snapshot().state == pet::PetState::Standby);
    assert(machine.snapshot().expression == pet::PetExpression::Sleepy);

    machine.handleVisionEvent(faceEvent(500, -250, 1000));
    assert(machine.snapshot().state == pet::PetState::Attentive);
    assert(machine.snapshot().expression == pet::PetExpression::Curious);
    assert(machine.snapshot().eyeTargetX == 400);
    assert(machine.snapshot().eyeTargetY == -150);

    machine.handleVisionEvent(faceEvent(200, 0, 3500));
    assert(machine.snapshot().state == pet::PetState::Standby);
    assert(machine.snapshot().expression == pet::PetExpression::Neutral);
    assert(machine.snapshot().eyeTargetX == 0);
    assert(machine.snapshot().eyeTargetY == 0);

    machine.handleVisionEvent(faceEvent(-1000, 1000, 0));
    assert(machine.snapshot().state == pet::PetState::Attentive);
    assert(machine.snapshot().eyeTargetX == -800);
    assert(machine.snapshot().eyeTargetY == 600);

    vision::VisionEvent lost;
    lost.type = vision::VisionEventType::FaceLost;
    machine.handleVisionEvent(lost);
    assert(machine.snapshot().state == pet::PetState::Standby);
    assert(machine.snapshot().expression == pet::PetExpression::Neutral);

    vision::VisionEvent timeout;
    timeout.type = vision::VisionEventType::VisionTimeout;
    machine.handleVisionEvent(timeout);
    assert(machine.snapshot().state == pet::PetState::NoVision);
    assert(machine.snapshot().expression == pet::PetExpression::Sleepy);
    assert(machine.snapshot().eyeTargetX == 0);
    assert(machine.snapshot().eyeTargetY == 0);

    vision::VisionEvent available;
    available.type = vision::VisionEventType::VisionAvailable;
    machine.handleVisionEvent(available);
    assert(machine.snapshot().state == pet::PetState::Standby);

    return 0;
}
