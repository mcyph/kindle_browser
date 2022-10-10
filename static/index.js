// https://github.com/osdroid/noxquest_kindle-tty/blob/master/client.js

var active = false;

var IGNORE_ABOVE = 1300;
var SCREEN_WIDTH = 1200; // NOTE ME!
//var SCREEN_WIDTH = 800*3;

if (true) {
    var TIMES_BY = 2.9;
    var TIMES_EVENTS_BY = 0.6;
} else {
    var TIMES_BY = 1.55;
    var TIMES_EVENTS_BY = 0.65;
}

const startListener = function() {
    if (active)	{
        return;
    }
    active = true;
    var jobId = 0;
    
    var messageDiv = document.getElementById('messageDiv');
    var topEl = document.getElementById('topEl');
    var inputDummy = document.getElementById('input_dummy');
    var chromiumCanvas = document.getElementById('chromiumCanvas');
    var wsConn = new WebSocket('ws://' + window.location.hostname + ":8080/ws");

    var ctx = chromiumCanvas.getContext('2d');

    //ctx.imageSmoothingEnabled = false;

    function sendJSON(obj) {
        if ('left' in obj) {
            obj['left'] *= TIMES_EVENTS_BY;
            obj['top'] *= TIMES_EVENTS_BY;
        }
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
        setMessage("");
        wsConn.send('firstData!');
        sendJSON({ type: 'command', command: 'initialFrame' });
    }
    wsConn.onclose = function(e) {
        setMessage("Disconn. " + JSON.stringify(e));
        active = false;
    }
    wsConn.onerror = function(e, code) {
        setMessage("ERROR " + code + e);
    }

    var darknessTypes = {
        0: '#000000',
        1: '#333333',
        2: '#545454',
        3: '#AAAAAA',
        4: '#FFFFFF',
    };
    var darknessNums = {
        0: 0,
        1: 32,
        2: 160,
        3: 220,
        4: 255,
    };
    var lineData = {
        0: ctx.createImageData(SCREEN_WIDTH, TIMES_BY*10),
        1: ctx.createImageData(SCREEN_WIDTH, TIMES_BY*10),
        2: ctx.createImageData(SCREEN_WIDTH, TIMES_BY*10),
        3: ctx.createImageData(SCREEN_WIDTH, TIMES_BY*10),
        4: ctx.createImageData(SCREEN_WIDTH, TIMES_BY*10),
    };

    for (var x=0; x<(SCREEN_WIDTH*TIMES_BY*10*4); x+=4) {
        for (var y=0; y<5; y++) {
            for (var z=0; z<4; z++) {
                if (z === 3) {
                    lineData[y].data[x + z] = 255;
                } else {
                    lineData[y].data[x + z] = darknessNums[y];
                }
            }
        }
    }

    var offset = 0;

    wsConn.onmessage = function(message) {
        /*offset++;
        if (offset === 2) {
            offset = 0;
        }*/

        var data = JSON.parse(message.data);
        var rleData = data.imageData;
        var y;

        try {
            for (y=0; y<rleData.length; y++) {
                var currentX = 0;
                ctx.beginPath();

                for (var x=0; x<rleData[y].length; x += 2) {
                    var darkness = rleData[y][x],
                        howLongFor = rleData[y][x+1];

                    /*ctx.beginPath();
                    ctx.fillStyle = darknessTypes[darkness];
                    ctx.fillRect(
                        parseInt(data.left+(currentX*TIMES_BY)), parseInt(data.top + initialY + y*TIMES_BY),
                        howLongFor*TIMES_BY, TIMES_BY
                    );
                    ctx.closePath();*/

                    ctx.putImageData(
                        lineData[darkness],
                        Math.round((data.left+currentX) * TIMES_BY),
                        Math.round(((data.top)+y) * TIMES_BY) + offset,
                        0, 0,
                        Math.round(howLongFor * TIMES_BY), // TIMES_BY*
                        2.1 //Math.round(TIMES_BY)
                    );
                    currentX += howLongFor;
                }

                ctx.closePath();
            }
        } catch(e) {
            setMessage("MSG ERROR: "+e);
        }
        setTimeout(function() {
            sendJSON({ type: 'command', command: 'readyForMore' });
        }, 0);
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