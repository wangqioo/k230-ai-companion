#include <cassert>
#include <cstdint>
#include <vector>

#include "../../esp32/vision_receiver/vision_protocol.h"


static std::vector<uint8_t> bytes(const char* hex) {
    std::vector<uint8_t> result;
    while (*hex) {
        char pair[3] = {hex[0], hex[1], 0};
        result.push_back(static_cast<uint8_t>(strtoul(pair, nullptr, 16)));
        hex += 2;
    }
    return result;
}


int main() {
    using namespace vision;

    Parser parser;
    Frame frame;
    auto heartbeat = bytes("a55a01010001000003e80000f3c7");
    bool ready = false;
    for (uint8_t byte : heartbeat) {
        ready = parser.feed(byte, frame);
    }
    assert(ready);
    assert(frame.type == MessageType::Heartbeat);
    assert(frame.sequence == 1);
    assert(frame.timestampMs == 1000);

    auto face = bytes(
        "a55a01020002000003f2000f0000000001f401f40000041a00004bc36c"
    );
    ready = false;
    for (uint8_t byte : face) {
        ready = parser.feed(byte, frame);
    }
    assert(ready);
    FaceObservation observation;
    assert(decodeFace(frame, observation));
    assert(observation.centerX == 0);
    assert(observation.centerY == 0);
    assert(observation.width == 500);
    assert(observation.height == 500);
    assert(observation.yawCentidegrees == 1050);
    assert(observation.confidence == 75);

    auto corrupt = heartbeat;
    corrupt.back() ^= 0xFF;
    ready = false;
    for (uint8_t byte : corrupt) {
        ready = parser.feed(byte, frame) || ready;
    }
    assert(!ready);
    for (uint8_t byte : heartbeat) {
        ready = parser.feed(byte, frame) || ready;
    }
    assert(ready);

    VisionFreshness freshness(500);
    assert(!freshness.available(1000));
    freshness.noteValidFrame(1000);
    assert(freshness.available(1500));
    assert(!freshness.available(1501));

    return 0;
}
