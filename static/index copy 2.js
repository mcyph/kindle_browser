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
    ctx.mozImageSmoothingEnabled    = false;
    ctx.oImageSmoothingEnabled      = false;
    ctx.webkitImageSmoothingEnabled = false;
    ctx.msImageSmoothingEnabled     = false;
    ctx.imageSmoothingEnabled       = false;

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

            image.onload = function() {
                ctx.drawImage(image, data.left, data.top);
                delete image;
            };
            image.src = "data:image/gif;base64,"+data.imageData;
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
