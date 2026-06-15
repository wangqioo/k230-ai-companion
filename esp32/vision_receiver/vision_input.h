#pragma once

#include <cstddef>
#include <cstdint>

#include "vision_protocol.h"


namespace vision {

enum class VisionEventType : uint8_t {
    VisionAvailable,
    FaceVisible,
    FaceLost,
    Heartbeat,
    VisionError,
    VisionTimeout,
    ProtocolWarning,
};

struct VisionEvent {
    VisionEventType type = VisionEventType::Heartbeat;
    uint32_t receivedAtMs = 0;
    uint16_t sequence = 0;
    uint32_t sourceTimestampMs = 0;
    FaceObservation face = {};
    uint16_t errorCode = 0;
};

constexpr std::size_t kMaxVisionEventsPerTick = 2;

struct EventBatch {
    VisionEvent events[kMaxVisionEventsPerTick] = {};
    std::size_t count = 0;

    bool push(const VisionEvent& event) {
        if (count >= kMaxVisionEventsPerTick) {
            return false;
        }
        events[count++] = event;
        return true;
    }
};

struct VisionSnapshot {
    bool visionAvailable = false;
    bool faceVisible = false;
    FaceObservation latestFace = {};
    uint32_t lastValidFrameMs = 0;
    uint16_t lastSequence = 0;
    bool hasSequence = false;
};

class VisionInput {
public:
    explicit VisionInput(uint32_t timeoutMs) : timeoutMs_(timeoutMs) {}

    EventBatch handleFrame(const Frame& frame, uint32_t nowMs);
    EventBatch tick(uint32_t nowMs);
    const VisionSnapshot& snapshot() const { return snapshot_; }

private:
    VisionEvent baseEvent(
        VisionEventType type,
        const Frame& frame,
        uint32_t nowMs
    ) const;
    void noteValidFrame(const Frame& frame, uint32_t nowMs);
    bool isTimedOut(uint32_t nowMs) const;

    uint32_t timeoutMs_;
    VisionSnapshot snapshot_ = {};
};

}  // namespace vision
