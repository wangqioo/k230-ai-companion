def _clamp(value, minimum, maximum):
    return minimum if value < minimum else maximum if value > maximum else value


def select_primary_face(faces):
    primary = None
    primary_area = -1
    for face in faces or ():
        box = face.get("box")
        if not box or len(box) < 4:
            continue
        if not face.get("euler") or len(face.get("euler")) < 3:
            continue
        width = box[2]
        height = box[3]
        if width <= 0 or height <= 0:
            continue
        area = width * height
        if area > primary_area:
            primary = face
            primary_area = area
    return primary


def make_primary_face_observation(faces, frame_size):
    if not frame_size or len(frame_size) < 2:
        raise ValueError("frame_size must contain width and height")

    frame_width, frame_height = frame_size[:2]
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")

    primary = select_primary_face(faces)
    if not primary:
        return None

    x, y, width, height = primary["box"][:4]
    pitch, yaw, roll = primary["euler"][:3]
    confidence = primary.get("confidence", 100)
    if isinstance(confidence, float):
        confidence_percent = int(round(confidence * 100))
    else:
        confidence_percent = int(round(confidence))

    center_x = int(round(((x + width / 2) * 2000 / frame_width) - 1000))
    center_y = int(round(((y + height / 2) * 2000 / frame_height) - 1000))
    normalized_width = int(round(width * 1000 / frame_width))
    normalized_height = int(round(height * 1000 / frame_height))

    return {
        "center_x": _clamp(center_x, -1000, 1000),
        "center_y": _clamp(center_y, -1000, 1000),
        "width": _clamp(normalized_width, 0, 1000),
        "height": _clamp(normalized_height, 0, 1000),
        "pitch_cd": _clamp(int(round(pitch * 100)), -32768, 32767),
        "yaw_cd": _clamp(int(round(yaw * 100)), -32768, 32767),
        "roll_cd": _clamp(int(round(roll * 100)), -32768, 32767),
        "confidence": _clamp(confidence_percent, 0, 100),
    }
