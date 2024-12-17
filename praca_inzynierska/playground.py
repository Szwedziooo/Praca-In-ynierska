from ultralytics import YOLO

# Load the YOLO11 model
model = YOLO("best_empty.pt")

# Export the model to NCNN format
model.export(format="ncnn")  # creates '/yolo11n_ncnn_model'

# Load the exported NCNN model
ncnn_model = YOLO("./best_empty_ncnn_model")

# Run inference
results = ncnn_model("Qr30.jpg")