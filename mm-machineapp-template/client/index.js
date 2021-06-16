/// <reference path="./js/jquery-3.5.1.min.js" />
/// <reference path="./js/kbd.js" />
/// <reference path="./ui.js" />
/// <reference path="./widgets.js" />

(function() {
    /******************************************************************
        Runtime API
    ******************************************************************/
    function lStartMachineApp(pConfiguration, pInStepperMode) {
        return fetch(`/run/start?stateStepperMode=${pInStepperMode ? 'true' : 'false'}`, {
            method: 'POST',
            body: JSON.stringify(pConfiguration),
            headers: {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json'
            }
        }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lStopMachineApp() {
        return fetch('/run/stop', { method: 'POST' }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lPauseMachineApp() {
        return fetch('/run/pause', { method: 'POST' }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lResumeMachineApp() {
        return fetch('/run/resume', { method: 'POST' }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lGetMachineAppState() {
        return fetch('/run/state').then(function(pResponse) {
            if (pResponse.status === 200) {
                return pResponse.json();
            } else {
                return undefined;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return undefined;
        });
    }

    function lGetEstop() {
        return fetch('/run/estop').then(function(pResponse) {
            if (pResponse.status === 200) {
                return pResponse.text().then(function(pText) {
                    return pText === 'true';
                });
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lSetEstop() {
        return fetch('/run/estop', { method: 'POST' }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lReleaseEstop() {
        return fetch('/run/releaseEstop', { method: 'POST' }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    function lResetSystem() {
        return fetch('/run/resetSystem', { method: 'POST' }).then(function(pResponse) {
            if (pResponse.status === 200) {
                return true;
            } else {
                return false;
            }
        }).catch(function(pReason) {
            console.exception('Failed to process request', pReason);
            return false;
        });
    }

    /******************************************************************
       General Tab
    ******************************************************************/

    let lState = 'idle';

    /**
     * Entry to the JavaScript of the program
     */
    function main() {
        const lIsPendant = window.location.hostname === '192.168.5.2';
        $('#estop-button').on('click', onEstopClicked)
        $('#app-launcher-button').on('click', onAppLauncherClicked);
        
        showContent();

        lGetMachineAppState().then(function(pState) {
            if (pState === undefined) {
                console.error('Failed to load the initial MachineApp state');
                return;
            }

            if (pState.isRunning) {
                onUpdateMessageReceived({
                    timeSeconds: Date.now(),
                    level: 'app_start',
                    message: 'MachineApp is running'
                });
                
                if (pState.isPaused) {
                    onUpdateMessageReceived({
                        timeSeconds: Date.now(),
                        level: 'app_pause',
                        message: 'MachineApp is paused'
                    });
                }
            }
        });

        connectToSocket();
        lGetEstop().then(function(pIsSet) {
            if (pIsSet) {
                console.log('Estop is active.');
                onEstopSet();
            }
        });

        if (lIsPendant) {
            // If we're on the pendant, we want to show the software keyboard
            // whenever someone touches an input. To do this, we scan the DOM
            // every 250 ms to add the keyboard if it is not present.
            keyboard_init();
            setInterval(keyboard_pre_bind, 250);
        }
    }
    
    // Connection to the notification Websocket
    let lWebsocketConnection = undefined;
    function connectToSocket() {
        const lWebsocketConnName = `ws://${window.location.hostname}:8081`;
        console.log('Connecting to socket at ' + lWebsocketConnName);
        lWebsocketConnection = new WebSocket(lWebsocketConnName,);
        lWebsocketConnection.onopen = function(pEvent) {
            console.log('Websocket is online');
        };
        lWebsocketConnection.onclose = function(pEvent) {
            console.log('Websocket connect closed', pEvent);
            const lTimeout = setTimeout(function() { 
                connectToSocket();
                clearInterval(lTimeout);
            }, 5000);
        };
        lWebsocketConnection.onmessage = function(pEvent) {
            const lMessageData = JSON.parse(pEvent.data);
            console.log('Received message from the socket connection', lMessageData);
            onUpdateMessageReceived(lMessageData);
        };
        lWebsocketConnection.onerror = function(pEvent) {
            console.error('Encountered error in websocket', pEvent);
        };
    }

    function addMessageToConsole(pIcon, pTime, pMessage) {
        const lDateTime = new Date(pTime),
            lRow = $('<tr>').prependTo($('#run-information-console')),
            lIcon = $('<td>').append($('<div>').addClass(pIcon)).appendTo(lRow),
            lTimeWrapper = $('<td>').appendTo(lRow),
            lTimeWrapperDiv = $('<div>').appendTo(lTimeWrapper),
            lTimeElement = $('<p>').text(lDateTime.toLocaleDateString()).appendTo(lTimeWrapperDiv).css('margin-bottom', '0').css('margin-top', '0'),
            lDateElement = $('<p>').text(lDateTime.toLocaleTimeString()).appendTo(lTimeWrapperDiv).css('margin-bottom', '0').css('margin-top', '0'),
            lDescription = $('<td>').append($('<span>').text(pMessage)).appendTo(lRow),
            lDismissBtn = $('<td>').append($('<button>').on('click', function() { 
                lRow.remove();
             }).text('Dismiss').addClass('widget-button primary link')).appendTo(lRow);
    }

    function onUpdateMessageReceived(pMessageData) {
        console.log(pMessageData);
        const lTimeSeconds = pMessageData.timeSeconds,
            lLevel = pMessageData.level,
            lMessageStr = pMessageData.message,
            lCustomPayload = pMessageData.customPayload;

        switch (lLevel) {
            case 'app_start': {
                lState = 'running';
                $('#run-start-button').empty().append($('<span>').addClass('fa fa-pause')).append($('<div>').text('PAUSE')).addClass('running');
                $('#run-stop-button').addClass('running');
                $('#run-debug-button').attr('disabled', 'disabled');
                addMessageToConsole('fa fa-play', lTimeSeconds, lMessageStr);
                break;
            }
            case 'app_complete': {
                lState = 'idle';
                $('#run-start-button').empty().append($('<span>').addClass('fa fa-play')).append($('<div>').text('START')).removeClass('running');
                $('#run-stop-button').removeClass('running').empty().append($('<span>').addClass('fa fa-stop')).append($('<div>').text('STOP'));
                $('#run-debug-button').removeAttr('disabled');
                addMessageToConsole('fa fa-stop', lTimeSeconds, lMessageStr);
                break;
            }
            case 'app_pause': {
                $('#run-start-button').empty().append($('<span>').addClass('fa fa-play')).append($('<div>').text('RESUME')).addClass('running');
                lState = 'paused';
                addMessageToConsole('fa fa-pause', lTimeSeconds, lMessageStr);
                break;
            }
            case 'app_resume': {
                $('#run-start-button').empty().append($('<span>').addClass('fa fa-pause')).append($('<div>').text('PAUSE')).addClass('running');
                lState = 'running';
                addMessageToConsole('fa fa-play', lTimeSeconds, lMessageStr);
                break;
            }
            case 'app_state_change': {
                addMessageToConsole('fa fa-arrow-right', lTimeSeconds, lMessageStr);
                break;
            }
            case 'app_estop_set': {
                addMessageToConsole('fa fa-info-circle', lTimeSeconds, lMessageStr);
                onEstopSet();

                if (lState === 'running' || lState === 'paused') {
                    $('#run-start-button').empty().append($('<span>').addClass('fa fa-play')).append($('<div>').text('START')).removeClass('running');
                    $('#run-stop-button').removeClass('running').empty().append($('<span>').addClass('fa fa-stop')).append($('<div>').text('STOP'));
                    $('#run-debug-button').removeAttr('disabled');
                    lState = 'idle';
                }
                break;
            }
            case 'app_estop_release': {
                addMessageToConsole('fa fa-info-circle', lTimeSeconds, lMessageStr);
                onEstopReleased();
                break;
            }
            case 'info': {
                addMessageToConsole('fa fa-info-circle', lTimeSeconds, lMessageStr);
                break;
            }
            case 'warning': {
                addMessageToConsole('fa fa-exclamation-triangle', lTimeSeconds, lMessageStr);
                break;
            }
            case 'error': {
                addMessageToConsole('fa fa-exclamation-triangle', lTimeSeconds, lMessageStr);
                break;
            }
        }

        onNotificationReceived(lLevel, lMessageStr, lCustomPayload);
    }

    function showContent() {
        const lRunTimeConfiguration = getDefaultConfiguration();
        $('#general-configuration-editor').empty().append(buildEditor(lRunTimeConfiguration));

        const lRunStartButton = $('#run-start-button').on('click', function() {
            const lPreviousElementContents = lRunStartButton.html()
            lRunStartButton.empty();
            lRunStartButton.append($('<div>').addClass('widget-spin-loader'));

            switch (lState) {
                case 'idle': {
                    lStartMachineApp(lRunTimeConfiguration, false).then(function(pSuccess) {
                        if (pSuccess) {
                            console.log('Successfully started the MachineApp');
                        } else {
                            console.error('Failed to start the MachineApp');
                            $('#run-start-button').empty().html(lPreviousElementContents);
                        }
                    });
                    break;
                }
                case 'running': {
                    lPauseMachineApp().then(function(pSuccess) {
                        if (pSuccess) {
                            console.log('Successfully pause the MachineApp');
                        } else {
                            console.error('Failed to pause the MachineApp');
                            $('#run-start-button').empty().html(lPreviousElementContents);
                        }
                    });
                    break;
                }
                case 'paused': {
                    lResumeMachineApp().then(function(pSuccess) {
                        if (pSuccess) {
                            console.log('Successfully resumed the MachineApp');
                        } else {
                            console.error('Failed to resume the MachineApp');
                            $('#run-start-button').empty().html(lPreviousElementContents);
                        }
                    });
                    break;
                }
            }
        });

        const lRunDebugButton = $('#run-debug-button').on('click', function() {
            switch (lState) {
                case 'idle': {
                    const lPreviousElementContents = lRunDebugButton.html()
                    lRunDebugButton.empty();
                    lRunDebugButton.append($('<div>').addClass('widget-spin-loader'));
                    lStartMachineApp(lRunTimeConfiguration, true).then(function(pSuccess) {
                        if (pSuccess) {
                            console.log('Successfully started the MachineApp');
                        } else {
                            console.error('Failed to start the MachineApp');
                        }
                        lRunDebugButton.empty().html(lPreviousElementContents);
                    });
                    break;
                }
            }
        });

        const lRunStopButton = $('#run-stop-button').on('click', function() {
            if (lState === 'idle') {
                console.warn('Cannot stop a MachineApp that is not running');
                return;
            }
            const lPreviousElementContents = lRunStopButton.html();
            lRunStopButton.empty();
            lRunStopButton.append($('<div>').addClass('widget-spin-loader'));

            lStopMachineApp().then(function(pSuccess) {
                if (pSuccess) {
                    console.log('Successfully stopped the MachineApp');
                } else {
                    console.error('Failed to stop the machine app');
                    lRunStopButton.empty().html(lPreviousElementContents);
                }
            })
        });
    }

     // Estop functionality
    function onEstopClicked() {
        console.log('Estop button clicked.');
        lSetEstop().then(function(pSuccess) {
            if (pSuccess) {
                console.log('Successfully sent the estop request');
            } else {
                console.error('Failed to estop');
            }
        })
    }

    function onEstopSet() {
        if ($('#estop-modal').length > 0) {
            return;
        }

        const lEstopModal = lCreateModal().attr('id', 'estop-modal'),
            lEstopModalHeader = lEstopModal.find('h3').text('E-Stop Activated').prepend($('<i>').addClass('fa fa-exclamation-triangle').css('padding-right', '0.5rem')),
            lBody = lEstopModal.find('.modal-body').addClass('v_layout').css('height', '100%').css('justify-content', 'center').css('align-items', 'center'),
            lActionRequired = $('<div>').append($('<h3>').text('Action Required')).appendTo(lBody),
            lEstopImage = $('<div>').appendTo($('<img>').attr('src', '/images/estop.png')).appendTo(lBody),
            lFirstInfo = $('<div>').append($('<p>').text('Ensure your E-Stop buttons are released. Click to release software stop.')).appendTo(lBody),
            lReleaseButton = $('<div>').append($('<button>').addClass('widget-button danger').text('RELEASE').on('click', function() {
                lReleaseEstop().then(function(pSuccess) {
                    if (pSuccess) {
                        console.log('Successfully released the estop');
                    } else {
                        console.error('Failed to release the estop');
                    }
                })
            })).appendTo(lBody),
            lSecondInfo = $('<div>').append($('<p>').text('When ready, click to reset your machine')).appendTo(lBody),
            lResetButton = $('<div>').append($('<button>').addClass('widget-button success').text('RESET').on('click', function() {
                lResetSystem().then(function(pSuccess) {
                    if (pSuccess) {
                        console.log('Successfully reset the system');
                    } else {
                        console.error('Failed to reset the system');
                    }
                })
            })).appendTo(lBody);

    }

    function onEstopReleased() {
        $('#estop-modal').remove();
    }

    // Going to the control center
    function onAppLauncherClicked() {
        location.href = `${window.location.protocol}//${window.location.hostname}`;
    }
    
    $(document).ready(main);
})()