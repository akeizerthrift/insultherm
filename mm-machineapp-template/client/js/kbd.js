/*$.kbd-0.5.1;(c)2018 - Mntn(r) <https://mn.tn/> c/o Benjamin Lips <g--[AT]--mn.tn>;MIT-Licensed <https://mit-license.org/>;For documentation, see <https://github.com/mntn-dev/kbd/>*/

/**
 * Function to create a keyboard instance
 */
function keyboard_init(){
    // IMPORTANT to call numpad first, because only kbd performs the binding (keys<->events)
    $.kbd_numpad({
        hidden: true,
        input: input_cb,
    });
    $.kbd({
        hidden: true,
        input: input_cb,
    });
}


/**
 * Function to add the class keyboard to the relevant items
 * being input fields of type text and number
 */
function keyboard_pre_bind(){
    var inputs = document.getElementsByTagName('input');
    for (var i=0; i<inputs.length; i++){
        // Input type text that is not already registered as keyboard
        if (inputs[i].type == "text" && inputs[i].className.includes('keyboard') != true ){
            inputs[i].className += ' keyboard';
        }
        // New number input
        else if (inputs[i].type == "number"){
            inputs[i].type = "tel";
            inputs[i].className += ' keyboard';
        }
    } 
    keyboard_bind();
}


/**
 * Function to bind relevent items to the keyboard
 * they correspond to 'keyboard' class objects
 */
function keyboard_bind(){
    // Show and hide the keyboard for each element that requires keyboard use
    // These elements are member of class keyboard
    var keyboard_items = document.getElementsByClassName('keyboard');
    for (var i=0; i<keyboard_items.length; i++){
        if (keyboard_items[i].type == "tel"){
            keyboard_items[i].addEventListener('focus', $.kbd_numpad.show);
            keyboard_items[i].addEventListener('blur', $.kbd_numpad.hide);
        }
        else {
            keyboard_items[i].addEventListener('focus', $.kbd.show);
            keyboard_items[i].addEventListener('blur', $.kbd.hide);
        }
        keyboard_items[i].addEventListener('keyup', function(){$.focusInValue = document.activeElement.value;});
        // Disable spellcheck for textarea inputs (avoid red underlign)
        if (keyboard_items[i].type == "textarea"){keyboard_items[i].spellcheck = false;}
    }  
}

/**
 * Function to process a pressed character on the virtual keyboard
 * Add or remove the pressed key
 * Avoid special character problems
 * Manage caret position
 */
function input_cb(chr){

    var field; //Input field to modify

    // Figure out focused element type
    if(document.activeElement.type == "textarea"){
        field = document.activeElement.innerHTML;
        // Look out for special characters causing trouble
        field = field.replace(/&amp;/g, '&').replace(/&gt;/g,'>').replace(/&lt;/g,'<');
    }
    else if (document.activeElement.type == "text" || document.activeElement.type == "tel"){field = document.activeElement.value;}
    else {return}

    var startPos = document.activeElement.selectionStart;
    var endPos = document.activeElement.selectionEnd;
    
    // Backspace (remove character)
    if(chr==$.BS){
        // If we want to only delete one character, else we want to delete the selected text
        if(startPos == endPos){startPos=startPos-1}

        // Create new field value
        field = field.substring(0, startPos)
            + field.substring(endPos, field.length);

        // Update the element
        if(document.activeElement.type == "textarea"){document.activeElement.innerHTML = field;}
        else if (document.activeElement.type == "text" || document.activeElement.type == "tel"){document.activeElement.value = field;}

        // Update cursor position
        document.activeElement.setSelectionRange(startPos,startPos);
    }

    // Add pressed key
    else {

        // Change key value and hide kbd if ENTER was pressed (only on alphanumeric kbd)
        if (chr == $.OK){
            document.activeElement.blur();
            return;
        }

        // Create new field value
        field = field.substring(0, startPos)
            + chr
            + field.substring(endPos, field.length);

        // Update the element
        if(document.activeElement.type == "textarea"){document.activeElement.innerHTML = field;}
        else if (document.activeElement.type == "text" || document.activeElement.type == "tel"){document.activeElement.value = field;}

        // Update cursor position
        document.activeElement.setSelectionRange(startPos+1,startPos+1);
    }

    // Trigger oninput event
    var event = new Event('input');
    document.activeElement.dispatchEvent(event);
}


/**
 * Function to adjust scroll when showing keyboard
 */
function scroll_showKeyboard(keyboard_name){
    // Get keyboard height, and add that element at the end of the page
    var keyboard_height = $(keyboard_name).height(); // TO DO
    document.getElementById('scroll').style.height = eval("'" + keyboard_height + "px'");
    document.getElementById('scroll').display = 'block';
    
    //Scroll to the right latitude
    // Remaining screen space is : screen height - (keyboard height + focused element height)
    // Remaining display content is : focused element top position
    // Scroll lattitude is : remaining display content height - remaining screen space height
    var scroll_margin = 20; //8px for reading comfort
    var scroll_latitude = $(":focus").offset().top - (window.innerHeight - ( keyboard_height + $(":focus").height() ));
    window.scrollTo(0,scroll_latitude+scroll_margin);

    //Disable scrolling possibility ?
    //document.body.style.overflow = 'hidden';
}

/**
 * Function to undo scroll when hiding keyboard
 */
function scroll_hideKeyboard(){
    document.getElementById('scroll').style.height = '0px';
    document.getElementById('scroll').display = 'none';
    //Re-enable scrolling possibility ?
    //document.body.style.overflow = 'visible';
}

; (function ($) {

    $.kbd = function (_) {

        // If a kbd keyboard is already defined, return and don't build another one
        if ($('#_kbd')[0] !== undefined) return;

        // Append keyboard wrapper to the body
        $('body').append('<div id="_kbd"><span id="_kbd_wrap"></span></div>');

        var _kbd_t = !1,
            _kbd_t2 = !1,
            q = '',
            // Toggle between ABC and 123 for the content of that one key
            tc = function (_) {
                c = _.data().c;
                cc = _.text();
                _.text(c);
                _.data('c', cc);
            },
            Q = function (_) {
                q = $('#__q').text();
                return ((_ === 0) ? q.toLowerCase() : q);
            },
            // Touch screen or not
            T = function () {
                return (window.ontouchstart !== undefined);
            },
            t_up = function (_) {
                if (T()) setTimeout(function (_) { _.removeClass('_kbd-h'); }, 1e2, _);
            }

        _k = 'q1w2e3r4t5y6u7i8o9p0__a@s#d$f_g&h-j+k(l)__{{\u25b2|data-c="\u25bc" class="l _caps"}}z/x%c*v,b"n!m?{{\u25c4|class="l" data-k="8"}}__{{123|class="l _alt" data-c="ABC"}}{{&nbsp;|class="xl" data-k="32"}}{{OK|class="l" data-k="13"}}';
        _e = {}; //Letters than span when long push on a key
        _e.q = '1';
        _e.w = '2';
        _e.e = '3';
        _e.r = '4';
        _e.t = '5';
        _e.y = '6';
        _e.u = '7';
        _e.i = '8';
        _e.o = '9';
        _e.p = '0';

        _e.k = '#{[<';
        _e.l = '#}]>';

        _e.z = '#\\';

        _e.v = '#;:.';
        _e.b = '#\'';

        // Break down to arrays
        _k = _k.split('__');

        // Dynamically creating the keyboard layout
        for (j = 0; j < _k.length; j++) { // For each array

            __k = _k[j].match(/\{\{(.*?)\}\}|[\S]{2}/g); // Break down the array to several keys

            for (i = 0; i < __k.length; i++) { // For each key in one array
                K = __k[i]; //one key (all the states)

                if (K[0] == '{') {
                    K = K.replace(/[\{\}]/g, '').split('|');
                }

                $('#_kbd_wrap').append('<button ' + (((typeof (K))[0] != 'o') ? 'data-a="' + (K[1] == '"' ? '&quot;' : K[1]) + '"' : K[1]) + (K[0] == 'q' ? ' id="__q"' : '') + '>' + K[0] + '</button>');
                
                if (_e[K[0]] !== undefined) { //If the key displays more options with long click
                    $('#_kbd_wrap button:last').wrap('<span class="_ext' + ((_e[K[0]][0] != '#') ? ' _ext-' + ((!$.isNumeric(_e[K[0]])) ? '1' : '0') : '') + '"></span>').parent().prepend('<span class="_ext-box" style="top:-' + (_e[K[0]] = _e[K[0]].replace('#', '')).length + '00%;">' + _e[K[0]].replace(/([\S\s])/g, '<button>$1</button>') + '</span>');
                }
                else if ((typeof (K))[0] == "s") { // Else, if the key is not a special key
                    $('#_kbd_wrap button:last').wrap('<span class="_ext"></span>');
                }
            }
        }


        // Binding events to buttons

        $('._caps').bind('mousedown touchstart', function (_) {
            _.preventDefault();
            if ((q = Q()).toLowerCase() != 'q') return;
            if (T()) $(this).trigger('mouseenter', !!1);
            // Long touch locks caps
            _kbd_t = setTimeout(function (_) { 
                _.addClass('_ext-caps'); 
                _.trigger('mouseup'); 
                _kbd_t = '%'; }, 
                750, $(this));
        })
            .bind('mouseup touchend', function (_) {
                _.preventDefault(); t_up($(this));
                if ((q = Q()).toLowerCase() != 'q' || _kbd_t == '%') return ((_kbd_t = !1)); if (_kbd_t) clearTimeout(_kbd_t);
                tc($(this)); if (q == 'Q' && $(this).hasClass('_ext-caps')) $(this).removeClass('_ext-caps');
                C = (q == 'Q') ? !1 : !!1; $('#_kbd button').each(function () { if ($(this).data().a !== undefined || $(this).parent().hasClass('_ext-box')) { $(this).text((C) ? $(this).text().toUpperCase() : (($(this).text() == 'SS') ? '\u00df' : $(this).text().toLowerCase())); } });
            });

        // This is the button to toggle between ABC and 123
        $('._alt').bind('mousedown', function (_) {
            // No focus on this element
            _.preventDefault();
            tc($(this));
            if (Q() == 'Q') {
                tc($('._caps')); $('._caps').removeClass('_ext-caps'); 
            }
            if (T()) { 
                $(this).trigger('mouseenter', !!1); 
                t_up($(this)); 
            }
            $('#_kbd button').each(function () { 
                if ((a = $(this).data().a) !== undefined) { 
                    $(this).data('a', $(this).text().toLowerCase()); 
                    $(this).text(a); } 
                });
            $('._ext:not(._ext-0)').toggleClass('_ext-1');
        }).bind('touchstart', function () { 
            $(this).trigger('mouseenter', !!1); 
        });

        $(__ = 'button[data-a],button[data-k],._ext-box button').bind('mouseup touchend', function (_$, r) {
            _$.preventDefault();
            if (_kbd_t && !r) { 
                clearTimeout(_kbd_t); 
                clearInterval(_kbd_t); 
            }
            if (T() && ($(this).prev('._ext-box').is(':visible'))) return;
            if ((typeof (_.input))[0] == 'f') _.input($(this).data().k ? String.fromCharCode($(this).data().k) : $(this).text());
            if (Q() == 'Q' && !$('._caps').hasClass('_ext-caps')) $('._caps').trigger('mouseup'); t_up($(this));
        }).bind('touchstart', function () { $(this).trigger('mouseenter', !!1); });

        $(__ + ',._caps,._alt').
            hover(
                function (_, r) { if (!T() || r !== undefined) $(this).addClass('_kbd-h'); },
                function () { if (!T()) $(this).removeClass('_kbd-h'); }
            );


        $('button[data-k]').bind('mousedown touchstart', function (_) { 
            _.preventDefault(); 
            _kbd_t = setTimeout(function (_) { 
                _kbd_t = setInterval(function () { 
                    _.trigger('mouseup', !!1); }, 50, _); 
                }, 2e2, $(this)); 
            });

        $('._ext')
            .bind('mousedown touchstart', function (_) { 
                _.preventDefault(); 
                if ($(this).hasClass('_ext-1') || ($(this).hasClass('_ext-0') && Q(0) == 'q')) { 
                    _kbd_t = setTimeout(function (_) { 
                        _.find('._ext-box').show(); 
                    }, 
                    750, $(this)); 
                    if (T()) _kbd_t2 = setTimeout(function (_) { 
                        _.find('._ext-box').hide(); t_up(_.children('button')) }, 3e3, $(this)); } })
            .bind('mouseup mouseleave', function (_) { _.preventDefault(); $(this).find('._ext-box:visible').hide(); if (_kbd_t) clearTimeout(_kbd_t); });


        $('._ext-box button').bind('touchend', function () { if (_kbd_t2) clearTimeout(_kbd_t2); $(this).parent().hide(); t_up($(this).parent().parent().children('button')); });

        if (_.hidden === !!1) return; $.kbd.show();

    },

    $.kbd_numpad = function (_) {

        // If a kbd keyboard is already defined, return and don't build another one
        if ($('#_kbd_numpad')[0] !== undefined) return;

        $('body').append('<div id="_kbd_numpad"><span id="_kbd_wrap_numpad"></span></div>');

        var _kbd_t = !1,
            _kbd_t2 = !1,
            q = '',
            Q = function (_) {
                q = $('#__q').text();
                return ((_ === 0) ? q.toLowerCase() : q);
            },
            T = function () {
                return (window.ontouchstart !== undefined);
            },
            t_up = function (_) {
                if (T()) setTimeout(function (_) { _.removeClass('_kbd-h'); }, 1e2, _);
            }

        // Numpad attempt
        _k = '7x8x9x__4x5x6x__1x2x3x__{{----|class="s" data-k="45"}}{{.|class="s" data-k="46"}}0x{{\u25c4|class="l" data-k="8"}}';
        _e = {};

        // Break down to arrays
        _k = _k.split('__');

        // Dynamically creating the keyboard layout
        for (j = 0; j < _k.length; j++) { // For each array

            __k = _k[j].match(/\{\{(.*?)\}\}|[\S]{2}/g); // Break down the array to several keys

            for (i = 0; i < __k.length; i++) { // For each key in one array
                K = __k[i]; //one key (all the states)

                if (K[0] == '{') {
                    K = K.replace(/[\{\}]/g, '').split('|');
                }

                $('#_kbd_wrap_numpad').append('<button ' + (((typeof (K))[0] != 'o') ? 'data-a="' + (K[1] == '"' ? '&quot;' : K[1]) + '"' : K[1]) + (K[0] == 'q' ? ' id="__q"' : '') + '>' + K[0] + '</button>');
                
                if (_e[K[0]] !== undefined) { //If the key displays more options with long click
                    $('#_kbd_wrap_numpad button:last').wrap('<span class="_ext' + ((_e[K[0]][0] != '#') ? ' _ext-' + ((!$.isNumeric(_e[K[0]])) ? '1' : '0') : '') + '"></span>').parent().prepend('<span class="_ext-box" style="top:-' + (_e[K[0]] = _e[K[0]].replace('#', '')).length + '00%;">' + _e[K[0]].replace(/([\S\s])/g, '<button>$1</button>') + '</span>');
                }
                else if ((typeof (K))[0] == "s") { // Else, if the key is not a special key
                    $('#_kbd_wrap_numpad button:last').wrap('<span class="_ext"></span>');
                }
            }
        }


        // Binding events to buttons
// NO BINDING HERE BECAUSE BIDING IS DONE BY THE SECOND KEYBOARD
/*
        $(__ = 'button[data-a],button[data-k],._ext-box button').bind('mouseup touchend', function (_$, r) {
            _$.preventDefault();
            if (_kbd_t && !r) { clearTimeout(_kbd_t); clearInterval(_kbd_t); }
            if (T()) if ($(this).prev('._ext-box').is(':visible')) return;
            if ((typeof (_.input))[0] == 'f') _.input($(this).data().k ? String.fromCharCode($(this).data().k) : $(this).text());
            if (Q() == 'Q' && !$('._caps').hasClass('_ext-caps')) $('._caps').trigger('mouseup'); t_up($(this));
        }).bind('touchstart', function () { $(this).trigger('mouseenter', !!1); });

        $(__ + ',._caps,._alt').
            hover(
                function (_, r) { if (!T() || r !== undefined) $(this).addClass('_kbd-h'); },
                function () { if (!T()) $(this).removeClass('_kbd-h'); }
            );


        $('button[data-k]').bind('mousedown touchstart', function (_) { 
            _.preventDefault(); 
            _kbd_t = setTimeout(function (_) { 
                _kbd_t = setInterval(function () { 
                    _.trigger('mouseup', !!1); }, 50, _); 
                }, 2e2, $(this)); 
            });

        $('._ext')
            .bind('mousedown touchstart', function (_) { 
                _.preventDefault(); 
                if ($(this).hasClass('_ext-1') || ($(this).hasClass('_ext-0') && Q(0) == 'q')) { 
                    _kbd_t = setTimeout(function (_) { 
                        _.find('._ext-box').show(); 
                    }, 
                    750, $(this)); 
                    if (T()) _kbd_t2 = setTimeout(function (_) { 
                        _.find('._ext-box').hide(); t_up(_.children('button')) }, 3e3, $(this)); } })
            .bind('mouseup mouseleave', function (_) { _.preventDefault(); $(this).find('._ext-box:visible').hide(); if (_kbd_t) clearTimeout(_kbd_t); });


        $('._ext-box button').bind('touchend', function () { if (_kbd_t2) clearTimeout(_kbd_t2); $(this).parent().hide(); t_up($(this).parent().parent().children('button')); });
*/
        if (_.hidden === !!1) return; $.kbd_numpad.show();

    },

        // Hide the keyboard
        $.kbd.hide = function (focusedElement) {  
            // Trigger change event if field was modified
            var focusOutValue = focusedElement.srcElement.value;
            if (focusOutValue != $.focusInValue){
                var event = new Event('change');
                focusedElement.srcElement.dispatchEvent(event);
            }
            // Hide kbd
            $('#_kbd').stop().animate({ bottom: '-100%' }, 250); 
            scroll_hideKeyboard();
        },
        
        // Show the keyboard
        $.kbd.show = function (focusedElement) { 
            //Save value before eventual modification
            $.focusInValue = focusedElement.srcElement.value;
            // Show kbd
            $('#_kbd').stop().animate({ bottom: 0 }, 250); 
            scroll_showKeyboard('#_kbd');
        },
        
        $.kbd.caps = function (_) { 
            q = $('#__q').text(); 
            if (_ === !!1 && q == 'q') $('._caps').addClass('_ext-caps').trigger('mouseup'); 
            else if (_ === !1 && q == 'Q') $('._caps').removeClass('_ext-caps').trigger('mouseup'); 
            else if (_ === undefined) $('._caps').trigger('mouseup'); },

        $.kbd.alt = function (_) { 
            q = $('#__q').text(); 
            if (_ === !!1 && q.toLowerCase() == 'q') $('._alt').trigger('click'); 
            else if (_ === !1 && q == '1') $('._alt').trigger('click'); 
            else if (_ === undefined) $('._alt').trigger('click'); 
        },       

        // Hide the keyboard
        $.kbd_numpad.hide = function (focusedElement) {  
            // Trigger change event if field was modified
            var focusOutValue = focusedElement.srcElement.value;
            if (focusOutValue != $.focusInValue){
                var event = new Event('change');
                focusedElement.srcElement.dispatchEvent(event);
            }
            // Hide kbd
            $('#_kbd_numpad').stop().animate({ bottom: '-100%' }, 250);  
            scroll_hideKeyboard();
        },
        
        // Show the keyboard
        $.kbd_numpad.show = function (focusedElement) { 
            //Save value before eventual modification
            $.focusInValue = focusedElement.srcElement.value;
            // Show kbd
            $('#_kbd_numpad').stop().animate({ bottom: '0%' }, 250); 
            scroll_showKeyboard('#_kbd_numpad');
        },


        $.BS = String.fromCharCode(8),
        $.OK = String.fromCharCode(13),
        $.focusInValue = ''


})(jQuery);
