#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <vector>

#include "../../esp32/vision_receiver/vision_input.h"


static std::vector<uint8_t> bytes(const char* hex) {
    std::vector<uint8_t> result;
    while (*hex) {
        char pair[3] = {hex[0], hex[1], 0};
        result.push_back(static_cast<uint8_t>(std::strtoul(pair, nullptr, 16)));
        hex += 2;
    }
    return result;
}


static vision::Frame parseFrame(const char* hex) {
    vision::Parser parser;
    vision::Frame frame;
    bool ready = false;
    for (uint8_t byte : bytes(hex)) {
        ready = parser.feed(byte, frame);
    }
    assert(ready);
    return frame;
}


static bool hasEvent(const vision::EventBatch& batch, vision::VisionEventType type) {
    for (std::size_t i = 0; i < batch.count; ++i) {
        if (batch.events[i].type == type) {
            return true;
        }
    }
    return false;
}


int main() {
    using namespace vision;

    auto heartbeat = parseFrame("a55a01010001000003e80000f3c7");
    auto face = parseFrame(
        "a55a01020002000003f2000f0000000001f401f40000041a00004bc36c"
    );
    auto faceLost = parseFrame("a55a01030003000003fc0000cae0");
    auto error = parseFrame("a55a017f0004000004060002002aa7b0");

    VisionInput input(500);

    EventBatch batch = input.handleFrame(heartbeat, 1000);
    assert(batch.count == 2);
    assert(hasEvent(batch, VisionEventType::VisionAvailable));
    assert(hasEvent(batch, VisionEventType::Heartbeat));
    assert(input.snapshot().visionAvailable);
    assert(!input.snapshot().faceVisible);

    batch = input.handleFrame(face, 1100);
    assert(batch.count == 1);
    assert(batch.events[0].type == VisionEventType::FaceVisible);
    assert(batch.events[0].face.width == 500);
    assert(batch.events[0].face.yawCentidegrees == 1050);
    assert(input.snapshot().faceVisible);

    batch = input.handleFrame(faceLost, 1200);
    assert(batch.count == 1);
    assert(batch.events[0].type == VisionEventType::FaceLost);
    assert(input.snapshot().visionAvailable);
    assert(!input.snapshot().faceVisible);

    batch = input.tick(1700);
    assert(batch.count == 0);
    batch = input.tick(1701);
    assert(batch.count == 1);
    assert(batch.events[0].type == VisionEventType::VisionTimeout);
    assert(!input.snapshot().visionAvailable);
    assert(!input.snapshot().faceVisible);

    batch = input.tick(1800);
    assert(batch.count == 0);

    batch = input.handleFrame(heartbeat, 1900);
    assert(batch.count == 2);
    assert(hasEvent(batch, VisionEventType::VisionAvailable));
    assert(hasEvent(batch, VisionEventType::Heartbeat));

    batch = input.handleFrame(error, 1950);
    assert(batch.count == 1);
    assert(batch.events[0].type == VisionEventType::VisionError);
    assert(batch.events[0].errorCode == 42);
    assert(input.snapshot().visionAvailable);

    return 0;
}
