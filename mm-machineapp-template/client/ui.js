/// <reference path="./widgets.js" />

/**
 * Populates the configuration editor in the 'Execute' panel with this default data
 */
function getDefaultConfiguration() {
    onNotificationReceived('app_start', 'App Started');

    if (document.cookie) {
        var lSplitCookies = document.cookie.split(';');
        for (var lIdx = 0; lIdx < lSplitCookies.length; lIdx++) {
            var lSplitToken = lSplitCookies[lIdx].split('=');
            if (lSplitToken.length >= 2 && lSplitToken[0] == 'config') {
                return JSON.parse(lSplitToken[1]);
            }
        }
    }

    return {
        home: false,
        prepare_new_roll: false,
        first_roll: false,
        manual_cut: false,
        replace_tape: false,
        cut_tape: false,
        singleBubble: false,
        doubleBubble: false,
        material_length: 0,
        sheet_count: 0,
        reset_running_total_cuts: false,
        /*
        ball_screw_pos: 50,
        regrip1_distance: 1000,                        
        droop_length: 100,
        regrip2_distance: 1000,
        regrip2_delay: 1,
        regrip2_speed: 500,
        regrip2_accel: 2000,
        vehicle_speed: 50,
        vehicle_accel: 500,
        nozzle_linear_pos1: 100,
        nozzle_linear_pos2: 150,
        nozzle_linear_pos3: 50,
        nozzle_rotation_pos1: 45,
        nozzle_rotation_pos2: 25,
        nozzle_rotation_pos3: 75,
        nozzle_P2_delay: 3,
        nozzle_P3_delay: 4,
        nozzle_cycle_time_1_2: 12,
        nozzle_cycle_time_2_3: 12,
        mobile_gripper_open_delay: 2,
        hot_wire_on_delay: 1,
        hot_wire_hold_delay: 2,
        fix_gripper_open_delay: 3,
        timing_belt_speed: 150,
        timing_belt_accel: 200,
        */
    }
}

/**
 * Constructs the editor that you see above the play/stop buttons in the 'Execute' panel
 * @param {Object} pConfiguration editable configuration 
 */
function buildEditor(pConfiguration) {
    function lUpdateCookies() {
        document.cookie = 'config=' + JSON.stringify(pConfiguration) + ';';
    }

    const lEditorWrapper = $('<div>').addClass('configuration-editor'),
        lGetMode = function() {
            if (pConfiguration.home) { return 'home'; }
            if (pConfiguration.prepare_new_roll) { return 'prepare_new_roll'; }
            if (pConfiguration.first_roll) { return 'first_roll'; }
            if (pConfiguration.manual_cut) { return 'manual_cut'; }
            if (pConfiguration.replace_tape) { return 'replace_tape'; }
            if (pConfiguration.cut_tape) { return 'cut_tape'; }
        },
        lMode = selectInput('Start sequence', lGetMode(), [
            { key: "Home", value: "home" },
            { key: "Prepare new roll", value: "prepare_new_roll" },
            { key: "First roll", value: "first_roll" },
            { key: "Manual cut", value: "manual_cut" },
            { key: "Replace tape", value: "replace_tape" },
            { key: "Cut tape", value: "cut_tape" },
        ], function(pSelection) {
            pConfiguration.home = false;
            pConfiguration.prepare_new_roll = false;
            pConfiguration.first_roll = false;
            pConfiguration.manual_cut = false;
            pConfiguration.replace_tape = false;
            pConfiguration.cut_tape = false;

            pConfiguration[pSelection] = true;
            lUpdateCookies();
        }).appendTo(lEditorWrapper),
        
        lGetType = function() {
            if (pConfiguration.mylar) { return 'mylar'; }
            if (pConfiguration.asj) { return 'asj'; }
        },
        lType = selectInput('Material Type', lGetType(), [
            { key: "Mylar", value: "mylar" },
            { key: "ASJ", value: "asj" },
        ], function(pSelection) {
            pConfiguration.mylar = false;
            pConfiguration.asj = false;
            
            pConfiguration[pSelection] = true;
            lUpdateCookies();
        }).appendTo(lEditorWrapper),
        
        lMaterialLength = numericInput('Material Length (inches)', pConfiguration.material_length, function(pValue) {
            if (pValue >= 0 && pValue <= 2400) {
                pConfiguration.material_length = pValue;
                lUpdateCookies();
            } else {
                lMaterialLength.find('input').val(pConfiguration.material_length);
            }
        }).appendTo(lEditorWrapper),
        lSheetCount = numericInput('Number of Sheets', pConfiguration.sheet_count, function(pValue) {
            if (pValue >=0 && pValue <= 1000) {
            pConfiguration.sheet_count = pValue;
            lUpdateCookies();
            } else {
                lSheetCount.find('input').val(pConfiguration.sheet_count);
            
            }
        }).appendTo(lEditorWrapper),
        
        lResetCount = checkbox('Reset Running Total Cuts', pConfiguration.reset_running_total_cuts, function(pValue) {
            pConfiguration.reset_running_total_cuts = pValue;
            lUpdateCookies();
        }).appendTo(lEditorWrapper);
        
         /*
        ldroop_length = numericInput('Droop Length (mm)', pConfiguration.droop_length, function(pValue) {
            pConfiguration.droop_length = pValue;
            lUpdateCookies();
        }).appendTo(lEditorWrapper),
        lregrip2_distance = numericInput('Re-Grip 2 Distance (mm)', pConfiguration.regrip2_distance, function(pValue) {
            if (pValue > 0 && pValue <= 1575) {
            pConfiguration.regrip2_distance = pValue;
            lUpdateCookies();
            } else {
                lregrip2_distance.find('input').val(pConfiguration.regrip2_distance);
            }
        }).appendTo(lEditorWrapper),
        lregrip2_delay = numericInput('Delay Before Regrip2 (sec)', pConfiguration.regrip2_delay, function(pValue) {
            if (pValue > 0 && pValue <= 30) {
            pConfiguration.regrip2_delay = pValue;
            lUpdateCookies();
            } else {
                lregrip2_delay.find('input').val(pConfiguration.regrip2_delay);
            }
        }).appendTo(lEditorWrapper),
        lregrip2_speed = numericInput('Speed of Mobile Gripper for Regrip2 (mm/s)', pConfiguration.regrip2_speed, function(pValue) {
            if (pValue > 0 && pValue <= 10000) {
            pConfiguration.regrip2_speed = pValue;
            lUpdateCookies();
            } else {
                lregrip2_speed.find('input').val(pConfiguration.regrip2_speed);
            }
        }).appendTo(lEditorWrapper),
        lregrip2_accel = numericInput('Accel of Mobile Gripper for Regrip2 (mm/s^2)', pConfiguration.regrip2_accel, function(pValue) {
            if (pValue > 0 && pValue <= 10000) {
            pConfiguration.regrip2_accel = pValue;
            lUpdateCookies();
            } else {
                lregrip2_accel.find('input').val(pConfiguration.regrip2_accel);
            }
        }).appendTo(lEditorWrapper),
        lvehicle_speed = numericInput('Speed of Mobile Gripper to Track Vehicle (mm/s)', pConfiguration.vehicle_speed, function(pValue) {
            if (pValue > 0 && pValue <= 10000) {
            pConfiguration.vehicle_speed = pValue;
            lUpdateCookies();
            } else {
                lvehicle_speed.find('input').val(pConfiguration.vehicle_speed);
            }
        }).appendTo(lEditorWrapper),
        lvehicle_accel = numericInput('Accel of Mobile Gripper to Track Vehicle (mm/s^2)', pConfiguration.vehicle_accel, function(pValue) {
            if (pValue > 0 && pValue <= 10000) {
            pConfiguration.vehicle_accel = pValue;
            lUpdateCookies();
            } else {
                lvehicle_accel.find('input').val(pConfiguration.vehicle_accel);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_linear_pos1 = numericInput('Nozzle First Position Linear (mm)', pConfiguration.nozzle_linear_pos1, function(pValue) {
            if (pValue >= 0 && pValue <= 200) {
            pConfiguration.nozzle_linear_pos1 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_linear_pos1.find('input').val(pConfiguration.nozzle_linear_pos1);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_rotation_pos1 = numericInput('Nozzle First Position Rotation (deg)', pConfiguration.nozzle_rotation_pos1, function(pValue) {
            if (pValue >= 0 && pValue <= 80) {
            pConfiguration.nozzle_rotation_pos1 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_rotation_pos1.find('input').val(pConfiguration.nozzle_rotation_pos1);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_linear_pos2 = numericInput('Nozzle Second Position Linear (mm)', pConfiguration.nozzle_linear_pos2, function(pValue) {
            if (pValue >= 0 && pValue <= 200) {
            pConfiguration.nozzle_linear_pos2 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_linear_pos2.find('input').val(pConfiguration.nozzle_linear_pos2);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_linear_pos3 = numericInput('Nozzle Third Position Linear (mm)', pConfiguration.nozzle_linear_pos3, function(pValue) {
            if (pValue >= 0 && pValue <= 200) {
            pConfiguration.nozzle_linear_pos3 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_linear_pos3.find('input').val(pConfiguration.nozzle_linear_pos3);
            }
        }).appendTo(lEditorWrapper),
        
       
        lnozzle_rotation_pos3 = numericInput('Nozzle Third Position Rotation (deg)', pConfiguration.nozzle_rotation_pos3, function(pValue) {
            if (pValue >= 0 && pValue <= 80) {
            pConfiguration.nozzle_rotation_pos3 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_rotation_pos3.find('input').val(pConfiguration.nozzle_rotation_pos3);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_P2_delay = numericInput('Nozzle Delay Before Pos 1-2 Move (sec)', pConfiguration.nozzle_P2_delay, function(pValue) {
            if (pValue >= 0.1 && pValue <= 30) {
            pConfiguration.nozzle_P2_delay = pValue;
            lUpdateCookies();
            } else {
                lnozzle_P2_delay.find('input').val(pConfiguration.nozzle_P2_delay);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_P3_delay = numericInput('Nozzle Delay Before Pos 2-3 Move (sec)', pConfiguration.nozzle_P3_delay, function(pValue) {
            if (pValue >= 0.1 && pValue <= 30) {
            pConfiguration.nozzle_P3_delay = pValue;
            lUpdateCookies();
            } else {
                lnozzle_P3_delay.find('input').val(pConfiguration.nozzle_P3_delay);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_cycle_time_1_2 = numericInput('Nozzle Cycle Time Pos 1-2 (sec)', pConfiguration.nozzle_cycle_time_1_2, function(pValue) {
            if (pValue >= 0.1 && pValue <= 30) {
            pConfiguration.nozzle_cycle_time_1_2 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_cycle_time_1_2.find('input').val(pConfiguration.nozzle_cycle_time_1_2);
            }
        }).appendTo(lEditorWrapper),
        lnozzle_cycle_time_2_3 = numericInput('Nozzle Cycle Time Pos 2-3 (sec)', pConfiguration.nozzle_cycle_time_2_3, function(pValue) {
            if (pValue >= 0.1 && pValue <= 30) {
            pConfiguration.nozzle_cycle_time_2_3 = pValue;
            lUpdateCookies();
            } else {
                lnozzle_cycle_time_2_3.find('input').val(pConfiguration.nozzle_cycle_time_2_3);
            }
        }).appendTo(lEditorWrapper),
        lmobile_gripper_open_delay = numericInput('Mobile Gripper Open Delay (sec)', pConfiguration.mobile_gripper_open_delay, function(pValue) {
            if (pValue >= 0 && pValue <= 30) {
            pConfiguration.mobile_gripper_open_delay = pValue;
            lUpdateCookies();
            } else {
                lmobile_gripper_open_delay.find('input').val(pConfiguration.mobile_gripper_open_delay);
            }
        }).appendTo(lEditorWrapper),
        lhot_wire_on_delay = numericInput('Hot Wire Start Delay (sec)', pConfiguration.hot_wire_on_delay, function(pValue) {
            if (pValue >= 0 && pValue <= 30) {
            pConfiguration.hot_wire_on_delay = pValue;
            lUpdateCookies();
            } else {
                lhot_wire_on_delay.find('input').val(pConfiguration.hot_wire_on_delay);
            }
        }).appendTo(lEditorWrapper),
        lhot_wire_hold_delay = numericInput('Hot Wire Hold Delay (sec)', pConfiguration.hot_wire_hold_delay, function(pValue) {
            if (pValue >= 0 && pValue <= 5) {
            pConfiguration.hot_wire_hold_delay = pValue;
            lUpdateCookies();
            } else {
                lhot_wire_hold_delay.find('input').val(pConfiguration.hot_wire_hold_delay);
            }
        }).appendTo(lEditorWrapper),
        lfix_gripper_open_delay = numericInput('Fixed Gripper Open Delay (sec)', pConfiguration.fix_gripper_open_delay, function(pValue) {
            if (pValue >= 0 && pValue <= 30) {
            pConfiguration.fix_gripper_open_delay = pValue;
            lUpdateCookies();
            } else {
                lfix_gripper_open_delay.find('input').val(pConfiguration.fix_gripper_open_delay);
            }
        }).appendTo(lEditorWrapper),
        ltiming_belt_speed = numericInput('Timing Belt Speed (mm/s)', pConfiguration.timing_belt_speed, function(pValue) {
            pConfiguration.timing_belt_speed = pValue;
            lUpdateCookies();
        }).appendTo(lEditorWrapper),
        ltiming_belt_accel = numericInput('Timing Belt Acceleration (mm/s^2)', pConfiguration.timing_belt_accel, function(pValue) {
            pConfiguration.timing_belt_accel = pValue;
            lUpdateCookies();
        }).appendTo(lEditorWrapper);

        */
    
    return lEditorWrapper;
}

/**
 * Message received from the Notifier on the backend
 * @param {NotificationLevel} pLevel
 * @param {string} pMessageStr 
 * @param {Object | None} pMessagePayload 
 */
function onNotificationReceived(pLevel, pMessageStr, pMessagePayload) {

    const lCustomContainer = $('#custom-container');

    function lCreateDioDisplay(pLabel, pId) {
        const lWrapper = $('<div>').appendTo(lCustomContainer),
            lInput = $('<input>').attr('type', 'radio').attr('id', pId).appendTo(lWrapper);
            lLabel = $('<label>').text(pLabel).appendTo(lWrapper);
    }


    function lCreateTextDisplay(pLabel, pId) {
        const lWrapper = $('<div>').appendTo(lCustomContainer),
            lInput = $('<input>').attr('type', 'text').attr('id', pId).attr('placeholder', pLabel).appendTo(lWrapper);
            lLabel = $('<label>').text(pLabel).appendTo(lWrapper);
    }

    if (pLevel === 'app_start') {
        lCustomContainer.empty();
        lCreateTextDisplay('State', 'state');
        lCreateTextDisplay('Sheets Left to Cut','sheets_cut');
        // lCreateTextDisplay('Roll Sensor','roll_sensor')
        lCreateTextDisplay('Running Total Cuts','running_total_cuts')
        
        return;
    }

    if (pLevel === 'io_state') {
        const name = pMessagePayload.name,
            value = Number(pMessagePayload.value) === 1;

        $('#' + name).prop('checked', value);
    }

    if (pLevel !== 'ui_info') {
        return;
    }
    if (pMessagePayload.ui_state != undefined) {
        $('#state').val(pMessagePayload.ui_state);
    }

    if (pMessagePayload.ui_sheets_cut != undefined) {
        $('#sheets_cut').val(pMessagePayload.ui_sheets_cut);
    }

    // if (pMessagePayload.ui_roll_sensor != undefined) {
    //     $('#roll_sensor').val(pMessagePayload.ui_roll_sensor);
    // }
    if (pMessagePayload.ui_running_total_cuts != undefined) {
        $('#running_total_cuts').val(pMessagePayload.ui_running_total_cuts);
    }

    // if (pMessagePayload.ui_brake_retract_cmd !== undefined) {
    //     $('#brake_retract_cmd').prop('checked', pMessagePayload.ui_brake_retract_cmd);
    // }
    // if (pMessagePayload.ui_brake_retracted !== undefined) {
    //     $('#brake_retracted').prop('checked', pMessagePayload.ui_brake_retracted);
    // }
    // if (pMessagePayload.ui_brake_extend_cmd !== undefined) {
    //     $('#brake_extend_cmd').prop('checked', pMessagePayload.ui_brake_extend_cmd);
    // }
    // if (pMessagePayload.ui_brake_extended !== undefined) {
    //     $('#brake_extended').prop('checked', pMessagePayload.ui_brake_extended);
    // }
}