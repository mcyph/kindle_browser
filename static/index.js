// https://github.com/osdroid/noxquest_kindle-tty/blob/master/client.js

var active = false;

var IGNORE_ABOVE = 1300;
var SCREEN_WIDTH = 1236; // NOTE ME!
//var SCREEN_WIDTH = 800*3;

if (false) {
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
        0: ctx.createImageData(SCREEN_WIDTH, 20),
        1: ctx.createImageData(SCREEN_WIDTH, 20),
        2: ctx.createImageData(SCREEN_WIDTH, 20),
        3: ctx.createImageData(SCREEN_WIDTH, 20),
        4: ctx.createImageData(SCREEN_WIDTH, 20),
    };

    for (var x=0; x<(SCREEN_WIDTH * 20); x+=4) {
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
    var cursorId = 0;

    wsConn.onmessage = function(message) {
        /*offset++;
        if (offset === 2) {
            offset = 0;
        }*/

        var data = JSON.parse(message.data);

        if (data['type'] === 'cursor_move') {
            var useCursorId = ++cursorId;
            setTimeout(function () {
                if (cursorId !== useCursorId) {
                    return;
                }
                var cursor = document.getElementById('cursor');
                data['relative_y'] -= 30; // HACK!
                data['relative_x'] -= 5; // HACK!
                cursor.style.left = data['relative_x'] * TIMES_BY + 'px';
                cursor.style.top = data['relative_y'] * TIMES_BY + 'px';
            }, 0);
            return;
        }

        var unRLEData = toByteArray(data.imageData);
        var b = fflate.gunzipSync(unRLEData);
        var o = [];
        for (var i=0; i<b.length; i++) {
            o.push(String.fromCharCode(b[i]));
        }
        var rleData = JSON.parse(o.join(""));

        var y;
        var numOps = 0;

        try {

            for (var useDarkness=0; useDarkness<5; useDarkness++) {
                ctx.beginPath();
                ctx.fillStyle = darknessTypes[useDarkness];

                for (y = 0; y < rleData.length; y++) {
                    var currentX = 0;

                    for (var x = 0; x < rleData[y].length; x += 2) {
                        var darkness = rleData[y][x],
                            howLongFor = rleData[y][x + 1];

                        if (darkness === useDarkness) {
                            if (true) {
                                //ctx.beginPath();
                                //ctx.fillStyle = darknessTypes[darkness];
                                ctx.rect(
                                    Math.round(data.left + (currentX * TIMES_BY)),
                                    Math.round(data.top + y * TIMES_BY),
                                    Math.round(howLongFor * TIMES_BY),
                                    Math.round(TIMES_BY)
                                );
                                //ctx.closePath();
                            } else {
                                ctx.putImageData(
                                    lineData[darkness],
                                    Math.round((data.left + currentX) * TIMES_BY),
                                    Math.round(((data.top) + y) * TIMES_BY) + offset,
                                    0, 0,
                                    Math.round(howLongFor * TIMES_BY), // TIMES_BY*
                                    Math.round(TIMES_BY)
                                );
                            }
                        }
                        currentX += howLongFor;
                        numOps++;
                    }
                }

                ctx.fill();
                ctx.closePath();
            }
        } catch(e) {
            setMessage("MSG ERROR: "+e);
        }
        setTimeout(function() {
            sendJSON({ type: 'command', command: 'readyForMore' });
        }, numOps > 2000 ? 0 : 0);
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
