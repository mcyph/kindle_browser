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
    var wsCursorConn = new WebSocket('ws://' + window.location.hostname + ":8080/wsCursor");

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
    };
    inputDummy.onkeyup = function(e) {
        sendKeyEvent('keyup', e);
    };
    inputDummy.onkeypress = function(e) {
        sendKeyEvent('keypress', e);
    };

    window.sendCmd = function(evt, cmd) {
        evt.preventDefault();
        evt.stopPropagation();
        sendJSON({ type: 'command', command: cmd });
    };

    window.navigateTo = function(url) {
        sendJSON({ type: 'command', command: 'navigate', url: url });
        toggleNavMenu();
    };

    document.addEventListener('mousemove', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            sendJSON({type: 'mouseMove', left: e.pageX, top: e.pageY});
        }
    });
    document.addEventListener('mousedown', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            sendJSON({ type: 'mouseDown', left: e.pageX, top: e.pageY });
        }
    });
    document.addEventListener('mouseup', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            sendJSON({type: 'mouseUp', left: e.pageX, top: e.pageY});
        }
    });
    document.addEventListener('click', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            sendJSON({type: 'click', left: e.pageX, top: e.pageY});
        }
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
    };
    wsConn.onclose = function(e) {
        setMessage("Disconn. " + JSON.stringify(e));
        active = false;
    };
    wsConn.onerror = function(e, code) {
        setMessage("ERROR " + code + e);
    };

    wsCursorConn.onopen = function() {
        alert("OPEN!")
    };
    wsCursorConn.onclose = function(e) {};
    wsCursorConn.onerror = function(e, code) {};

    var lineData = [];
    var DIVISOR = 32;

    for (var i=0; i<Math.ceil(255/DIVISOR); i++) {
        var imData = ctx.createImageData(1300, 5);
        for (var j=0; j<1300*4*5; j+=4) {
            imData.data[j+0] = i * DIVISOR;
            imData.data[j+1] = i * DIVISOR;
            imData.data[j+2] = i * DIVISOR;
            imData.data[j+3] = 255;
        }
        lineData.push(imData);
    }

    var cursorId = 0;
    //ctx.scale(TIMES_BY, TIMES_BY);

    wsCursorConn.onmessage = function(message) {
        var data = JSON.parse(message.data);
        alert(data);

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
    };

    wsConn.onmessage = function(message) {
        var data = JSON.parse(message.data);

        var x = 0;
        var y = 0;
        var total = 0;
        var darkness, runsFor;
        var rleData = atob(data.imageData);
        var width = data.width;
        var height = data.height;
        var SINGLE_VALUES_FROM = Math.floor((255 / DIVISOR)) + 1;

        //alert(!rleData || rleData.length)

        var drawFor = function(darkness, amount) {
            try {
                ctx.putImageData(
                    lineData[darkness],
                    Math.ceil((data.left + x) * TIMES_BY),
                    Math.ceil((data.top + y) * TIMES_BY),
                    0, 0,
                    Math.ceil(TIMES_BY * amount),
                    Math.ceil(TIMES_BY)
                );
            } catch (e) {
                alert("ERROR DRAWFOR: "+darkness+" "+amount+" "+lineData.length+" "+lineData[darkness]);
                throw e;
            }
        };

        try {
            for (var i=0; i<rleData.length; i++) {
                var j = rleData.charCodeAt(i);
                if (j >= SINGLE_VALUES_FROM) {
                    darkness = j - SINGLE_VALUES_FROM;
                    runsFor = 1;
                } else {
                    darkness = j;
                    runsFor = rleData.charCodeAt(i+1);
                    i += 1;
                }
                total += runsFor;

                while ((x+runsFor) > width) {
                    // Goes to next line
                    var toEndOfLine = width-x;
                    if (toEndOfLine) {
                        drawFor(darkness, toEndOfLine);
                        x += toEndOfLine;
                    }
                    runsFor -= toEndOfLine;
                    y += 1;
                    x = 0;
                }

                if (runsFor) {
                    // All on same line
                    drawFor(darkness, runsFor);
                    x += runsFor;
                }
            }
        } catch(e) {
            setMessage("MSG ERROR: "+e+" "+e.lineNumber);
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
