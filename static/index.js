// https://github.com/osdroid/noxquest_kindle-tty/blob/master/client.js

var active = false;

var viewportHeight = window.outerHeight;

var TIMES_BY = 1.54;
var TIMES_EVENTS_BY = window.devicePixelRatio > 1.0 ? 0.677 : 0.71;
TIMES_BY = (TIMES_BY * window.devicePixelRatio) - 0.12;

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

    // HACK!
    var controlsAt = ((window.devicePixelRatio > 1) ? viewportHeight : (viewportHeight*2)) - 15;
    document.getElementById('navControls').style.top =  controlsAt+'px';
    var IGNORE_ABOVE = controlsAt;

    var ctx = chromiumCanvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;

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

    var MOUSE_OFFSET_X = -15;
    var MOUSE_OFFSET_Y = -15;

    document.addEventListener('mousemove', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            sendJSON({type: 'mouseMove', left: e.pageX+MOUSE_OFFSET_X, top: e.pageY+MOUSE_OFFSET_Y});
            //updateCursorPosition(e.pageX+MOUSE_OFFSET_X, e.pageY+MOUSE_OFFSET_Y);
        }
    });
    document.addEventListener('mousedown', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            //sendJSON({ type: 'mouseDown', left: e.pageX, top: e.pageY });
            //updateCursorPosition(e.pageX+MOUSE_OFFSET_X, e.pageY+MOUSE_OFFSET_Y);
        }
    });
    document.addEventListener('mouseup', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            //sendJSON({type: 'mouseUp', left: e.pageX, top: e.pageY});
            //updateCursorPosition(e.pageX+MOUSE_OFFSET_X, e.pageY+MOUSE_OFFSET_Y);
        }
    });
    document.addEventListener('click', function(e) {
        if (e.pageY < IGNORE_ABOVE) {
            //sendJSON({type: 'click', left: e.pageX, top: e.pageY});
            //updateCursorPosition(e.pageX+MOUSE_OFFSET_X, e.pageY+MOUSE_OFFSET_Y);
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

    var lineData = [];
    var darknessValues = [];
    var DIVISOR = 64;
    var NUM_SHADES = Math.ceil(255/DIVISOR);
    var IMAGE_DATA_WIDTH = 2000;
    var IMAGE_DATA_HEIGHT = 150;

    for (var i=0; i<NUM_SHADES; i++) {
        var imData = ctx.createImageData(IMAGE_DATA_WIDTH, IMAGE_DATA_HEIGHT);
        var data = imData.data;
        var brightness = i * DIVISOR;

        if (i === NUM_SHADES-1) {
            brightness = 255;
        } else {
            brightness = Math.round(brightness * 0.8); // Increase contrast
        }

        for (var j=0; j<IMAGE_DATA_WIDTH*4*IMAGE_DATA_HEIGHT*2; j+=4) {
            data[j+0] = brightness;
            data[j+1] = brightness;
            data[j+2] = brightness;
            data[j+3] = 255;
        }

        lineData.push(imData);
        darknessValues.push(brightness);
    }

    var cursorId = 0;
    //ctx.scale(0.53, 0.55);

    var wsConn = new WebSocket('ws://' + window.location.hostname + ":8080/ws");
    var wsCursorConn = new WebSocket('ws://' + window.location.hostname + ":8080/wsCursor");

    wsConn.onopen = function() {
        setMessage("");
        //wsConn.send('firstData!');
        sendJSON({type: 'command', command: 'initialFrame'});
    };
    wsConn.onclose = function(e) {
        setMessage("Disconn. " + JSON.stringify(e));
        active = false;
    };
    wsConn.onerror = function(e, code) {
        setMessage("ERROR " + code + e);
    };

    wsCursorConn.onopen = function() {
    };
    wsCursorConn.onclose = function(e) {
    };
    wsCursorConn.onerror = function(e, code) {
    };

    var cursorMoveData = null;

    wsCursorConn.onmessage = function(message) {
        var data = JSON.parse(message.data);

        if (data['type'] === 'cursor_move') {
            var useCursorId = ++cursorId;
            cursorMoveData = data;

            setTimeout(function () {
                if (cursorId !== useCursorId) {
                    return;
                }
                //data['relative_y'] -= 28; // HACK!
                //data['relative_x'] -= 5; // HACK!
                updateCursorPosition(
                    data['relative_x'] * (1 / TIMES_EVENTS_BY),
                    data['relative_y'] * (1 / TIMES_EVENTS_BY)
                );
                cursorMoveData = null;
            }, 500);
            return;
        } else if (data['type'] === 'cursor_change') {
            var cursor = document.getElementById('cursor');
            cursor.src = data['data'];
        }
    };

    var updateCursorPosition = function(x, y) {
        var cursor = document.getElementById('cursor');
        cursor.style.left = x + 'px';
        cursor.style.top = y + 'px';
    };

    var drawForPx = 3;
    var iteration = 0;

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

        var drawFor = function (darkness, amount) {
            //drawForPx++;
            //if (drawForPx === Math.ceil(TIMES_BY)+1) {
            //    drawForPx = (Math.ceil(TIMES_BY) - 1) || 1;
            //}
            try {
                ctx.putImageData(
                    lineData[darkness],
                    Math.ceil((data.left + x) * TIMES_BY),
                    Math.ceil((data.top + y) * TIMES_BY),
                    0, 0,
                    Math.ceil(TIMES_BY * amount),
                    drawForPx
                );
            } catch (e) {
                alert("ERROR DRAWFOR: " + darkness + " " + amount + " " + lineData.length + " " + lineData[darkness]);
                throw e;
            }
        };

        // Get the most common shade
        var counts = {};
        for (var i = 0; i < rleData.length; i++) {
            var j = rleData.charCodeAt(i);
            if (j >= SINGLE_VALUES_FROM) {
                darkness = j - SINGLE_VALUES_FROM;
                runsFor = 1;
            } else {
                darkness = j;
                runsFor = rleData.charCodeAt(i + 1);
                i += 1;
            }
            counts[darkness] = (counts[darkness] || 0) + runsFor;
        }
        var longestRun = 0;
        var longestShade = null;

        for (var k in counts) {
            if (counts[k] > longestRun) {
                longestRun = counts[k];
                longestShade = parseInt(k);
            }
        }

        try {
            // Fill in the most common shade as background as a single operation
            var amountToGo = Math.ceil(TIMES_BY * data.height);
            //alert("NEW "+amountToGo);
            var currentY = 0;
            while (amountToGo > 0) {
                var amountThisTime = amountToGo > IMAGE_DATA_HEIGHT ? IMAGE_DATA_HEIGHT : amountToGo;
                ctx.putImageData(
                    lineData[longestShade],
                    Math.ceil(data.left * TIMES_BY),
                    currentY + Math.ceil(data.top * TIMES_BY),
                    0, 0,
                    Math.ceil(TIMES_BY * data.width),
                    amountThisTime
                );
                currentY += amountThisTime;
                amountToGo -= amountThisTime;
            }
            //alert("BREAK "+longestShade);

            for (var i = 0; i < rleData.length; i++) {
                var j = rleData.charCodeAt(i);
                if (j >= SINGLE_VALUES_FROM) {
                    darkness = j - SINGLE_VALUES_FROM;
                    runsFor = 1;
                } else {
                    darkness = j;
                    runsFor = rleData.charCodeAt(i + 1);
                    i += 1;
                }
                total += runsFor;

                while ((x + runsFor) > width) {
                    // Goes to next line
                    var toEndOfLine = width - x;
                    if (toEndOfLine) {
                        if (darkness !== longestShade) {
                            drawFor(darkness, toEndOfLine);
                        }
                        x += toEndOfLine;
                    }
                    runsFor -= toEndOfLine;
                    y += 1;
                    x = 0;
                }

                if (runsFor) {
                    // All on same line
                    if (darkness !== longestShade) {
                        drawFor(darkness, runsFor);
                    }
                    x += runsFor;
                }
            }
        } catch (e) {
            setMessage("MSG ERROR: " + e + " " + e.lineNumber);
        }

        // Update the cursor in one batch with the other updates
        // to prevent needing to do it separately on the eink display
        setTimeout(function() {
            if (cursorMoveData) {
                cursorId++; // Invalidate the current job
                updateCursorPosition(
                    cursorMoveData['relative_x'] * (1 / TIMES_EVENTS_BY),
                    cursorMoveData['relative_y'] * (1 / TIMES_EVENTS_BY)
                );
                cursorMoveData = null;
            }
        }, 0);

        setTimeout(function() {
            sendJSON({type: 'command', command: 'readyForMore'});
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
