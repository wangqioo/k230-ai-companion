#include "vision_input.h"


namespace vision {

VisionEvent VisionInput::baseEvent(
    VisionEventType type,
    const Frame& frame,
    uint32_t nowMs
) const {
    VisionEvent event;
    event.type = type;
    event.receivedAtMs = nowMs;
    event.sequence = frame.sequence;
    event.sourceTimestampMs = frame.timestampMs;
    return event;
}

void VisionInput::noteValidFrame(const Frame& frame, uint32_t nowMs) {
    snapshot_.lastValidFrameMs = nowMs;
    snapshot_.lastSequence = frame.sequence;
    snapshot_.hasSequence = true;
}

bool VisionInput::isTimedOut(uint32_t nowMs) const {
    return snapshot_.visionAvailable &&
           static_cast<uint32_t>(nowMs - snapshot_.lastValidFrameMs) > timeoutMs_;
}

EventBatch VisionInput::handleFrame(const Frame& frame, uint32_t nowMs) {
    EventBatch batch;
    const bool wasAvailable = snapshot_.visionAvailable;

    noteValidFrame(frame, nowMs);
    snapshot_.visionAvailable = true;
    if (!wasAvailable) {
        batch.push(baseEvent(VisionEventType::VisionAvailable, frame, nowMs));
    }

    switch (frame.type) {
        case MessageType::Heartbeat:
            batch.push(baseEvent(VisionEventType::Heartbeat, frame, nowMs));
            break;

        case MessageType::Face: {
            FaceObservation observation;
            if (decodeFace(frame, observation)) {
                snapshot_.latestFace = observation;
                snapshot_.faceVisible = true;
                VisionEvent event = baseEvent(
                    VisionEventType::FaceVisible,
                    frame,
                    nowMs
                );
                event.face = observation;
                batch.push(event);
            } else {
                batch.push(baseEvent(VisionEventType::ProtocolWarning, frame, nowMs));
            }
            break;
        }

        case MessageType::FaceLost:
            snapshot_.faceVisible = false;
            batch.push(baseEvent(VisionEventType::FaceLost, frame, nowMs));
            break;

        case MessageType::Error: {
            uint16_t errorCode = 0;
            if (decodeError(frame, errorCode)) {
                VisionEvent event = baseEvent(
                    VisionEventType::VisionError,
                    frame,
                    nowMs
                );
                event.errorCode = errorCode;
                batch.push(event);
            } else {
                batch.push(baseEvent(VisionEventType::ProtocolWarning, frame, nowMs));
            }
            break;
        }

        default:
            batch.push(baseEvent(VisionEventType::ProtocolWarning, frame, nowMs));
            break;
    }

    return batch;
}

EventBatch VisionInput::tick(uint32_t nowMs) {
    EventBatch batch;
    if (isTimedOut(nowMs)) {
        snapshot_.visionAvailable = false;
        snapshot_.faceVisible = false;

        VisionEvent event;
        event.type = VisionEventType::VisionTimeout;
        event.receivedAtMs = nowMs;
        event.sequence = snapshot_.lastSequence;
        batch.push(event);
    }
    return batch;
}

}  // namespace vision
