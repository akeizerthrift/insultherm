/**
 * Creates a Modal that gets appended to the main view
 */
function lCreateModal() {
    const lModalBackground = $('<div>').addClass('modal-background').appendTo($('#main-content')),
         lContainer = $('<div>').addClass('modal-container').appendTo(lModalBackground),
         lHeader = $('<header>').appendTo(lContainer),
         lHeaderTitle = $('<h3>').appendTo(lHeader),
         lBody = $('<div>').addClass('modal-body').appendTo(lContainer),
         lFooter = $('<footer>').appendTo(lContainer);

     return lModalBackground;
}

/**
 * Creates a textbox widget
 * @param {String} pLabel 
 * @param {String} pValue 
 * @param {function(value: String) => void} pOnChange 
 */
function textbox(pLabel, pValue, pOnChange) {
     const lWrapper = $('<div>').addClass('widget-wrapper').addClass('widget-textbox'),
         lLabel = pLabel ? $('<label>').text(pLabel).appendTo(lWrapper) : undefined,
         lInput = $('<input>').val(pValue).appendTo(lWrapper);

     if (pOnChange) {
         lInput.on('change', function() {
             pOnChange(lInput.val());
         });
     }

     return lWrapper;
 }

 /**
  * Creates a numeric textbox widget
  * @param {String} pLabel 
  * @param {Number} pValue 
  * @param {function(value: String) => void} pOnChange 
  */
 function numericInput(pLabel, pValue, pOnChange) {
     const lTextbox = textbox(pLabel, pValue, function(pNewValue) {
         const lNumVal = Number(pNewValue);
         if (isNaN(lNumVal)) {
             lTextbox.find('input').val(0);
         }

         pOnChange(lNumVal);
     });

     lTextbox.find('input').css('text-align', 'right').attr('type', 'number');

     return lTextbox;
 }

 /**
  * Creates a dropdown selector
  * @param {String} pLabel 
  * @param {Number | String} pValue 
  * @param {Array<{ key: String, value: String | number }} pOptionsList
  * @param {function(value: String) => void} pOnChange 
  */
 function selectInput(pLabel, pValue, pOptionsList, pOnChange) {
     const lWrapper = $('<div>').addClass('widget-wrapper'),
         lLabel = $('<label>').text(pLabel).appendTo(lWrapper),
         lSelectWrapper = $('<div>').addClass('widget-select').appendTo(lWrapper),
         lInput = $('<select>').appendTo(lSelectWrapper);

     lInput.on('change', function() {
         pOnChange(lInput.val());
     });
     
     pOptionsList.forEach(function(pOption) {
         $('<option>').text(pOption.key).attr('value', pOption.value).appendTo(lInput);
     });

     lInput.val(pValue);
     return lWrapper;
 }


 /**
  * Creates a checkbox widget
  * @param {String} pLabel 
  * @param {Boolean} pDefaultValue 
  * @param {function(value: Boolean) -> void} pOnChange 
  */
 function checkbox(pLabel, pDefaultValue, pOnChange) {
     const lWrapper = $('<label>').text(pLabel).addClass('widget-checkbox'),
         lInputElement = $('<input>').attr('type', 'checkbox').attr('checked', pDefaultValue).appendTo(lWrapper),
         lSpanElement = $('<span>').addClass('widget-checkmark').appendTo(lWrapper);

     lInputElement.on('change', function(pEvent) {
         pOnChange(Boolean(lInputElement.prop('checked')));
     });

     return lWrapper;
 }

 /**
  * Used to change the options in a selector
  * @param {JQuery<HTMLElement>} pSelect 
  * @param {Array<{ key: String, value: String | number }} pNewOptions 
  * @param {String | Number} pSelectedValue 
  */
 function updateSelectOptions(pSelect, pNewOptions, pSelectedValue) {
     const selectInput = pSelect.find('select');

     pSelect.find('option').remove();
     pNewOptions.forEach(function(pOption) {
         $('<option>').text(pOption.key).attr('value', pOption.value).appendTo(selectInput);
     });

     if (pNewOptions.find(function(pExisting) { return pExisting.value == pSelectedValue; })) {
         selectInput.val(pSelectedValue);
     } else if (pNewOptions.length > 0) {
         selectInput.val(pNewOptions[0].value);
     }
     
     selectInput.trigger('change');
 }

 /**
  * Display an error on any of the widgets
  * @param {JQuery<HTMLElement>} pWidget 
  * @param {String} pError 
  */
 function appendError(pWidget, pError) {
     return $('<div>').addClass('widget-error').appendTo(pWidget).text(pError);
 }

 /**
  * Clear an error on any of the widgets
  * @param {JQuery<HTMLElement>} pWidget 
  */
 function clearError(pWidget) {
     pWidget.find('.widget-error').remove();
 }