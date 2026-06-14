#pragma once

#include <cstddef>
#include <cstdint>


namespace vision {

constexpr uint8_t kVersion = 1;
constexpr std::size_t kHeaderSize = 12;
constexpr std::size_t kCrcSize = 2;
constexpr std::size_t kMaxPayloadSize = 256;
constexpr std::size_t kMaxFrameSize = kHeaderSize + kMaxPayloadSize + kCrcSize;

enum class MessageType : uint8_t {
    Heartbeat = 1,
    Face = 2,
    FaceLost = 3,
    Error = 127,
};

struct Frame {
    MessageType type = MessageType::Heartbeat;
    uint16_t sequence = 0;
    uint32_t timestampMs = 0;
    uint16_t payloadLength = 0;
    uint8_t payload[kMaxPayloadSize] = {};
};

struct FaceObservation {
    int16_t centerX = 0;
    int16_t centerY = 0;
    int16_t width = 0;
    int16_t height = 0;
    int16_t pitchCentidegrees = 0;
    int16_t yawCentidegrees = 0;
    int16_t rollCentidegrees = 0;
    uint8_t confidence = 0;
};

uint16_t crc16Ccitt(const uint8_t* data, std::size_t length);
bool decodeFace(const Frame& frame, FaceObservation& observation);

class Parser {
public:
    bool feed(uint8_t byte, Frame& frame);
    void reset();

private:
    uint8_t buffer_[kMaxFrameSize] = {};
    std::size_t length_ = 0;
    std::size_t expectedLength_ = 0;
};

class VisionFreshness {
public:
    explicit VisionFreshness(uint32_t timeoutMs) : timeoutMs_(timeoutMs) {}

    void noteValidFrame(uint32_t nowMs) {
        lastValidFrameMs_ = nowMs;
        hasFrame_ = true;
    }

    bool available(uint32_t nowMs) const {
        return hasFrame_ &&
               static_cast<uint32_t>(nowMs - lastValidFrameMs_) <= timeoutMs_;
    }

private:
    uint32_t timeoutMs_;
    uint32_t lastValidFrameMs_ = 0;
    bool hasFrame_ = false;
};

}  // namespace vision
