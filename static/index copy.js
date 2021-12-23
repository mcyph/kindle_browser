// https://github.com/osdroid/noxquest_kindle-tty/blob/master/client.js

var active = false;

const startListener = function() {
    if (active)	{
        return;
    }
    active = true;
    
    var messageDiv = document.getElementById('messageDiv')
    var topEl = document.getElementById('topEl')
    var canvas = document.getElementById("chromiumCanvas");
    var ctx = canvas.getContext("2d");
    var wsConn = new WebSocket('ws://' + window.location.hostname + ":8080/ws");

    function sendJSON(obj) {
        wsConn.send(JSON.stringify(obj));
    }

    document.addEventListener('mousemove', function(e) {
        sendJSON({ type: 'mouseMove', left: e.offsetX, top: e.offsetY });
    });
    document.addEventListener('mousedown', function(e) {
        sendJSON({ type: 'mouseDown', left: e.offsetX, top: e.offsetY });
    });
    document.addEventListener('mouseup', function(e) {
        sendJSON({ type: 'mouseUp', left: e.offsetX, top: e.offsetY });
    });
    document.addEventListener('click', function(e) {
        sendJSON({ type: 'click', left: e.offsetX, top: e.offsetY });
    });
    /*document.onscroll = function(e) {
        sendJSON({
            type: 'scroll',
            left: Math.max(document.documentElement.scrollLeft, document.body.scrollLeft),
            top: Math.max(document.documentElement.scrollTop, document.body.scrollTop),
        });
    }*/

    const setMessage = function(message) {
        messageDiv.innerHTML = message;
    };
    var toProcess = [];
    function clearDrawBuffer() {
        for (var i=0; i<toProcess.length; i++) {
            var image = toProcess[i][0];
            var left = toProcess[i][1];
            var top = toProcess[i][2];
            var width = toProcess[i][3];
            var height = toProcess[i][4];
            
            var ignore = false;
            for (var j=i+1; j<toProcess.length; j++) {
                if (left >= toProcess[j][1] && top >= toProcess[j][2] &&
                    (left+width) <= (toProcess[j][1]+toProcess[j][3]) && 
                    (top+height) <= (toProcess[j][2]+toProcess[j][4])) {
                    ignore = true;
                    break;
                }
            }
            
            if (!ignore) {
                ctx.drawImage(image, left, top);
            }
            image.src = 'about:blank';
            delete image;
        }
        toProcess = [];
    }
    var toProcessImages = [];

    wsConn.onopen = function() {
        setMessage("Active");
        wsConn.send('firstData!');
    }
    wsConn.onclose = function(e) {
        setMessage("Disconn. " + JSON.stringify(e));
        active = false;
    }
    wsConn.onerror = function(e, code) {
        setMessage("ERROR " + code + e);
    }
    wsConn.onmessage = function(message) {
        try {
            var image = new Image();
            var data = JSON.parse(message.data);
            var toProcessImagesOut = [];

            // Don't continue to load a JPEG if we're going to overwrite it immediately
            for (var j=0; j<toProcessImages.length; j++) {
                if (data.left >= toProcessImages[j][1] && data.top >= toProcessImages[j][2] &&
                    (data.left+data.width) <= (toProcessImages[j][1]+toProcessImages[j][3]) && 
                    (data.top+data.height) <= (toProcessImages[j][2]+toProcessImages[j][4])) {
                    toProcessImages[j].src = 'about:blank';
                } else {
                    toProcessImagesOut.push(toProcessImages[j])
                }
            }
            toProcessImages = toProcessImagesOut;

            image.onload = function() {
                //ctx.clearRect(data.left, data.top, data.width, data.height);
                //ctx.drawImage(image, data.left, data.top);
                toProcess.push([image, data.left, data.top, data.width, data.height]);
                delete image;
                delete data;
                setTimeout(clearDrawBuffer, 0);
            };
            image.src = "data:image/png;base64,"+data.imageData;
            toProcessImages.push([image, data.left, data.top, data.width, data.height])
            //setMessage("msg len: "+data.imageData.length);
        } catch(e) {
            setMessage("MSG ERROR");
        }
    }
}

const rotarContenedor = function() {
    try {
        startListener();
    } catch (e) {
        alert(e);
    }
}
setTimeout(rotarContenedor, 500);
