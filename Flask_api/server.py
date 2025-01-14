import flask
from flask import Flask, flash, request, redirect, url_for, render_template, Response
from werkzeug.utils import secure_filename
import os
from classify import *
import json
import datetime
import cv2
from listenToStream import *
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


UPLOAD_FOLDER = 'classify'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
app = flask.Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
file_path = './static/'
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["5000 per day", "100 per hour"]
)
# firebase = firebase.FirebaseApplication('https://capstonephoneapp-default-rtdb.firebaseio.com/', None)

camera = cv2.VideoCapture(0)
'''
for ip camera use - rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' 
for local webcam use cv2.VideoCapture(0)
'''
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():  
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            #cv2.imwrite('c1.jpg',frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload():

    imageFile = request.files["image"]
    print(imageFile)
    # if user does not select file, browser also
    # submit a empty part without filename
    filename = ""
    if imageFile.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if imageFile and allowed_file(imageFile.filename):
        filename = secure_filename(imageFile.filename)
        imageFile.save(os.path.join(file_path, filename))
        if(detect_face(file_path + filename)):
            classify_picture(filename)
            return "Good face"
        else:
            os.remove(file_path + filename)
            return "bad face"

    return "Sucessfully uploaded"



def classify_picture(filename):
    name = classify(file_path + filename)

    data = {}
    relation = ""
    description = ""
    with open('data.json') as f:
        data = json.load(f)

    for i in data["data"]:

        if i["name"] == name[0]:
            relation = i["relation"]
            description = i["description"]

    #check how many
    result = firebase.get('/log/', '')
    if (len(result) > 5):
        for i in result:
            firebase.delete('/log/', i)
    #put it into the database
    data = {
        "name": name[0],
        "probability":name[1],
        "relation": relation,
        "description": description,
        "picture": filename,
        "timestamp": datetime.now() 
    }

    result = firebase.post('/log/',data)
    print(result)

    return result
#
# listen for now has hardcoded instructor_id and course_id. Pass real user input as function arguments
#
@app.route('/classify', methods=['GET'])
@limiter.limit("0.2/second", override_defaults=True)
def classify_from_stream():
  listen()



#app.run(host="localhost", port=5000, debug=True, threaded=True)
app.run(host='0.0.0.0', port=5000, threaded=True)
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'