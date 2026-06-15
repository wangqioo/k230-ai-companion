#include "vision_protocol.h"
#include "vision_input.h"
#include "pet_state_machine.h"


constexpr int kK230RxPin = 16;
constexpr int kK230TxPin = 17;
constexpr uint32_t kBaudRate = 921600;
constexpr uint32_t kVisionTimeoutMs = 500;

HardwareSerial K230Serial(2);
vision::Parser parser;
vision::VisionInput visionInput(kVisionTimeoutMs);
pet::PetStateMachine petStateMachine;


void enterNoVisionState(const vision::VisionEvent& event) {
    (void)event;
    // Stop or center actuators here. ESP32 owns the product-safe behavior.
}


void applyPetSnapshot(const pet::PetSnapshot& snapshot) {
    (void)snapshot;
    // Drive display, audio, motors, or other outputs from this snapshot.
}


void handleVisionEvent(const vision::VisionEvent& event) {
    petStateMachine.handleVisionEvent(event);
    applyPetSnapshot(petStateMachine.snapshot());

    switch (event.type) {
        case vision::VisionEventType::FaceVisible:
            // Feed event.face into the ESP32-owned real-time state machine.
            break;
        case vision::VisionEventType::FaceLost:
            // Keep vision online, but clear face-dependent behavior.
            break;
        case vision::VisionEventType::VisionTimeout:
            enterNoVisionState(event);
            break;
        case vision::VisionEventType::VisionError:
            // K230 reported an inference/runtime error.
            break;
        default:
            break;
    }
}


void handleVisionEvents(const vision::EventBatch& batch) {
    for (std::size_t i = 0; i < batch.count; ++i) {
        handleVisionEvent(batch.events[i]);
    }
}


void setup() {
    Serial.begin(115200);
    K230Serial.begin(kBaudRate, SERIAL_8N1, kK230RxPin, kK230TxPin);
}


void loop() {
    vision::Frame frame;
    while (K230Serial.available()) {
        if (parser.feed(static_cast<uint8_t>(K230Serial.read()), frame)) {
            handleVisionEvents(visionInput.handleFrame(frame, millis()));
        }
    }

    handleVisionEvents(visionInput.tick(millis()));
}
