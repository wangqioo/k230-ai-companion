#include "vision_protocol.h"

#include <cstring>


namespace vision {
namespace {

constexpr uint8_t kMagic0 = 0xA5;
constexpr uint8_t kMagic1 = 0x5A;
constexpr std::size_t kFacePayloadSize = 15;

uint16_t readU16(const uint8_t* data) {
    return static_cast<uint16_t>(
        (static_cast<uint16_t>(data[0]) << 8) | data[1]
    );
}

int16_t readI16(const uint8_t* data) {
    return static_cast<int16_t>(readU16(data));
}

uint32_t readU32(const uint8_t* data) {
    return (static_cast<uint32_t>(data[0]) << 24) |
           (static_cast<uint32_t>(data[1]) << 16) |
           (static_cast<uint32_t>(data[2]) << 8) |
           static_cast<uint32_t>(data[3]);
}

}  // namespace

uint16_t crc16Ccitt(const uint8_t* data, std::size_t length) {
    uint16_t crc = 0xFFFF;
    for (std::size_t index = 0; index < length; ++index) {
        crc ^= static_cast<uint16_t>(data[index]) << 8;
        for (uint8_t bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000)
                      ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                      : static_cast<uint16_t>(crc << 1);
        }
    }
    return crc;
}

void Parser::reset() {
    length_ = 0;
    expectedLength_ = 0;
}

bool Parser::feed(uint8_t byte, Frame& frame) {
    if (length_ == 0) {
        if (byte == kMagic0) {
            buffer_[length_++] = byte;
        }
        return false;
    }

    if (length_ == 1) {
        if (byte == kMagic1) {
            buffer_[length_++] = byte;
        } else if (byte == kMagic0) {
            buffer_[0] = byte;
        } else {
            reset();
        }
        return false;
    }

    if (length_ >= kMaxFrameSize) {
        reset();
        return false;
    }
    buffer_[length_++] = byte;

    if (length_ == kHeaderSize) {
        if (buffer_[2] != kVersion) {
            reset();
            return false;
        }
        const uint16_t payloadLength = readU16(&buffer_[10]);
        if (payloadLength > kMaxPayloadSize) {
            reset();
            return false;
        }
        expectedLength_ = kHeaderSize + payloadLength + kCrcSize;
    }

    if (expectedLength_ == 0 || length_ < expectedLength_) {
        return false;
    }

    const uint16_t expectedCrc = readU16(&buffer_[expectedLength_ - kCrcSize]);
    const uint16_t actualCrc = crc16Ccitt(
        buffer_, expectedLength_ - kCrcSize
    );
    if (expectedCrc != actualCrc) {
        reset();
        return false;
    }

    frame.type = static_cast<MessageType>(buffer_[3]);
    frame.sequence = readU16(&buffer_[4]);
    frame.timestampMs = readU32(&buffer_[6]);
    frame.payloadLength = readU16(&buffer_[10]);
    if (frame.payloadLength) {
        std::memcpy(
            frame.payload, &buffer_[kHeaderSize], frame.payloadLength
        );
    }
    reset();
    return true;
}

bool decodeFace(const Frame& frame, FaceObservation& observation) {
    if (frame.type != MessageType::Face ||
        frame.payloadLength != kFacePayloadSize) {
        return false;
    }

    observation.centerX = readI16(&frame.payload[0]);
    observation.centerY = readI16(&frame.payload[2]);
    observation.width = readI16(&frame.payload[4]);
    observation.height = readI16(&frame.payload[6]);
    observation.pitchCentidegrees = readI16(&frame.payload[8]);
    observation.yawCentidegrees = readI16(&frame.payload[10]);
    observation.rollCentidegrees = readI16(&frame.payload[12]);
    observation.confidence = frame.payload[14];
    return true;
}

}  // namespace vision
