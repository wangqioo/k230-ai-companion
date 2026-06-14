#include "vision_protocol.h"


constexpr int kK230RxPin = 16;
constexpr int kK230TxPin = 17;
constexpr uint32_t kBaudRate = 921600;
constexpr uint32_t kVisionTimeoutMs = 500;

HardwareSerial K230Serial(2);
vision::Parser parser;
vision::VisionFreshness freshness(kVisionTimeoutMs);
vision::FaceObservation latestFace;
bool faceVisible = false;
bool visionWasAvailable = false;


void handleFrame(const vision::Frame& frame) {
    freshness.noteValidFrame(millis());

    if (frame.type == vision::MessageType::Face) {
        if (vision::decodeFace(frame, latestFace)) {
            faceVisible = true;
        }
    } else if (frame.type == vision::MessageType::FaceLost) {
        faceVisible = false;
    }
}


void enterNoVisionState() {
    faceVisible = false;
    // Stop or center actuators here. ESP32 owns the product-safe behavior.
}


void setup() {
    Serial.begin(115200);
    K230Serial.begin(kBaudRate, SERIAL_8N1, kK230RxPin, kK230TxPin);
}


void loop() {
    vision::Frame frame;
    while (K230Serial.available()) {
        if (parser.feed(static_cast<uint8_t>(K230Serial.read()), frame)) {
            handleFrame(frame);
        }
    }

    const bool visionAvailable = freshness.available(millis());
    if (visionWasAvailable && !visionAvailable) {
        enterNoVisionState();
    }
    visionWasAvailable = visionAvailable;

    if (visionAvailable && faceVisible) {
        // Feed latestFace into the ESP32-owned real-time state machine.
    }
}
