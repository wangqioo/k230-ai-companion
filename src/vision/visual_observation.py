def select_primary_face(faces):
    primary = None
    primary_area = -1
    for face in faces or ():
        box = face.get("box")
        if not box or len(box) < 4:
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
