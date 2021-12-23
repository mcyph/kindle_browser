// https://github.com/osdroid/noxquest_kindle-tty/blob/master/client.js

var active = false;

const startListener = function() {
    if (active)	{
        return;
    }
    active = true;
    
    var messageDiv = document.getElementById('messageDiv');
    var topEl = document.getElementById('topEl');
    var inputDummy = document.getElementById('input_dummy');
    var wsConn = new WebSocket('ws://' + window.location.hostname + ":8080/ws");

    function sendJSON(obj) {
        wsConn.send(JSON.stringify(obj));
    }

    function sendKeyEvent(keyEventType, e) {
        sendJSON({
            type: 'command',
            command: 'keyevent',
            keyEventType: keyEventType,
            altKey: e.altKey,
            shiftKey: e.shiftKey,
            ctrlKey: e.ctrlKey,
            charCode: e.charCode,
            keyCode: e.keyCode,
        });
    }

    inputDummy.onkeydown = function(e) {
        sendKeyEvent('keydown', e);
    }
    inputDummy.onkeyup = function(e) {
        sendKeyEvent('keyup', e);
    }
    inputDummy.onkeypress = function(e) {
        sendKeyEvent('keypress', e);
    }

    window.sendCmd = function(evt, cmd) {
        evt.preventDefault();
        evt.stopPropagation();
        sendJSON({ type: 'command', command: cmd });
    }

    window.navigateTo = function(url) {
        sendJSON({ type: 'command', command: 'navigate', url: url });
        toggleNavMenu();
    }

    const IGNORE_ABOVE = 1300;
    document.addEventListener('mousemove', function(e) {
        if (e.pageY < IGNORE_ABOVE)
            sendJSON({ type: 'mouseMove', left: e.pageX, top: e.pageY });
    });
    document.addEventListener('mousedown', function(e) {
        if (e.pageY < IGNORE_ABOVE)
            sendJSON({ type: 'mouseDown', left: e.pageX, top: e.pageY });
    });
    document.addEventListener('mouseup', function(e) {
        if (e.pageY < IGNORE_ABOVE)
            sendJSON({ type: 'mouseUp', left: e.pageX, top: e.pageY });
    });
    document.addEventListener('click', function(e) {
        if (e.pageY < IGNORE_ABOVE)
            sendJSON({ type: 'click', left: e.pageX, top: e.pageY });
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

    var images = [];
    var zIndex = 0
    wsConn.onmessage = function(message) {
        try {
            var image = new Image();
            var data = JSON.parse(message.data);

            var imagesOut = [];
            for (var i=0; i<images.length; i++) {
                const otherImage = images[i];

                if (data.left <= otherImage.left && 
                    data.top <= otherImage.top &&
                    (data.left+data.width) >= (otherImage.left+otherImage.width) &&
                    (data.top+data.height) >= (otherImage.top+otherImage.height)) {
                        otherImage.el.parentNode.removeChild(otherImage.el);
                } else {
                    imagesOut.push(otherImage);
                }
            }
            images = imagesOut;
            image.src = "data:image/png;base64,"+data.imageData;
            image.style.top = data.top+'px';
            image.style.left = data.left+'px';
            image.style.position = 'absolute';
            image.style.zIndex = zIndex++;
            document.body.insertBefore(image, document.body.firstChild);
            images.push({
                el: image,
                top: data.top,
                left: data.left,
                width: data.width,
                height: data.height,
            });
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


const toggleNavMenu = function() {
    const navMenu = document.getElementById('navMenu');
    if (navMenu.style.display == 'none') {
        navMenu.style.display = 'block';
    } else {
        navMenu.style.display = 'none';
    }
}