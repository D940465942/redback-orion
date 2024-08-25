import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
from utils import calculateHomography, transformPoints
from pymongo import MongoClient
from time import time

# Load the YOLO model
model = YOLO("yolov8n.pt")

# Connect to the MongoDB database
# and set up data recording
# client = MongoClient("")
# db = client["CrowdTracking"]
# collection = db["Crowd"]
# lastRecorded = time.time()


# Connect to the RTSP stream
# rtspUrl = "rtsp://"
rtspUrl = 0
cap = cv2.VideoCapture(rtspUrl)

trackHistory = defaultdict(list)

# Load the floor image
from floorReplica import floorReplica
canvasHeight = 1000
canvasWidth = 700
tilesX = 25
tilesY = 15
floorImage = floorReplica(canvasHeight, canvasWidth, tilesX, tilesY, rtspUrl)

height, width, channels = floorImage.shape

# Define the codec and create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video = cv2.VideoWriter('output.mp4', fourcc, 20.0, (width, height))

# Define the source and destination points for the homography matrix
# Calculate the homography matrix
ptsSRC = np.array([[28, 1158], [2120, 1112], [1840, 488], [350, 518], [468, 1144]])
ptsDST = np.array([[0, 990], [699, 988], [693, 658], [0, 661], [141, 988]])
homographyMatrix = calculateHomography(ptsSRC, ptsDST)

# Main loop
while True:
#while cap.isOpened():
    success, frame = cap.read()
    # if not success:
    #     raise Exception("Failed to read video stream - mapTracking.py - main loop")
    
    results = model.track(frame, persist=True, show=False, imgsz=1280, verbose=True)
    annotatedFrame = floorImage.copy()
    # if results[0].boxes is not None and hasattr(results[0].boxes, 'id'):
    try:
        if results[0].boxes is not None:
            # Check if the boxes attribute contains IDs
            if hasattr(results[0].boxes, 'id'):
                # Check if there are any detected boxes
                if results[0].boxes.id.numel() > 0:
                    # Convert tensor to NumPy array
                    boxes = results[0].boxes.xywh.cpu().numpy()
                    trackIDs = results[0].boxes.id.cpu().numpy()
                    print('Track IDs:', trackIDs)
                    # Copy floorImage only if objects are detected
                    annotatedFrame = floorImage.copy()

                    for trackID in np.unique(trackIDs):
                        history = trackHistory[trackID]
                        if len(history) > 1:
                            points = np.array(history, dtype=np.int32)
                            newPoints = transformPoints(points, homographyMatrix)
                            newPoints = newPoints.astype(np.int32)

                            cv2.polylines(annotatedFrame, [newPoints], isClosed=False, color=(0, 0, 255), thickness=2)

                    for box, trackID in zip(boxes, trackIDs):
                        x, y, w, h = box
                        center = (int(x), int(y + h / 2))
                        trackHistory[trackID].append(center)

                        if len(trackHistory[trackID]) > 50:
                            trackHistory[trackID].pop(0)
                    video.write(annotatedFrame)
                else:
                        print("No objects detected. No IDs available.")
            else:
                print("The 'id' attribute is not present in the boxes.")
        else:
                print("No boxes detected. The 'boxes' attribute is None.")
    except AttributeError as e:
                print(f"An AttributeError occurred: {e}")
    except Exception as e:
                print(f"An unexpected error occurred: {e}")   
        
    cv2.imshow("Map Tracking", annotatedFrame)
    cv2.imshow("Camera Feed", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

        

cap.release()
#video.release()
cv2.destroyAllWindows()
