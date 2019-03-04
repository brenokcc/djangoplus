var cursor = document;

function fakeMouse(){
    if($("#fake-cursor").length==0) {
        var img = $('<img id="fake-cursor">');
        img.attr('id', "fake-cursor");
        img.attr('src', "/static/images/hand.png");
        img.css('position', 'absolute');
        img.css('top', '300px');
        img.css('left', '300px');
        img.css('z-index', '99999999');
        img.appendTo(document.body);
    }
}

function fakeType(el, string, index){
      var val = string.substr(0, index + 1);
      el.val(val);
      if (index < string.length) {
        setTimeout(function(){ fakeType(el, string, index + 1); }, Math.random() * 200);
      }
      if(index==string.length-1){
          var daterangepicker = el.data('daterangepicker');
          if(daterangepicker) daterangepicker.hide();
      }
}


function moveMouseTo(lookup, f) {
    $("#fake-cursor").attr("src","/static/images/hand.png").show();
    var el = $(lookup).first();
    var top = el.first().offset()['top']+el.height()/2;
	var left = el.first().offset()['left']+el.width()/2;
	var lastClickedElement = null;
	window['mouse-top'] = top;
	window['mouse-left'] = left;
	$('#fake-cursor').animate({top:  top, left: left }, 1200, 'swing', function(){
	    if(lastClickedElement!=el) {
	        $("#fake-cursor").attr("src","/static/images/click.png");
            setTimeout(f, 500);
        }
	    lastClickedElement = el;
	});
}

function recursively(element){
    if(element.length==0 && cursor!=document) {
        if (cursor.parentNode != null) cursor = cursor.parentNode; else cursor = document;
        return true
    }
    return false
}

function isIntoView(elem)
{
    var docViewTop = $(window).scrollTop();
    var docViewBottom = docViewTop + $(window).height();

    var elemTop = elem.offset().top;
    var elemBottom = elemTop + elem.height();

    return ((elemBottom <= docViewBottom-200) && (elemTop-52 >= docViewTop));
}

function scroolToElement(element, callback){
    var lastScrooledElement = null;
    if(element.offset() && !isIntoView(element)) {
        var scrollData = { scrollTop: element.offset().top - $(window).height()/2 };
        if(window['display_fake_mouse']) var scroolSpeed = 1200;
        else var scroolSpeed = 0;
        $([document.documentElement, document.body]).animate(scrollData, scroolSpeed, 'swing', function (){
            if(lastScrooledElement!=element) callback();
            lastScrooledElement = element;
        });
    } else {
        callback();
    }
    return element
}

function typeReturn(element){
    element.trigger({type: 'keypress', which: 13, keyCode: 13});
}

function typeTab(element){
    element.trigger({type: 'keypress', which: 9, keyCode: 9});
}

function click(name, type, index){

    if(index==null) index = 0;

    var element = [];

    var menu = type==null || type=='menu';
    var link = type==null || type=='link';
    var button = type==null || type=='button';
    var tab = type == 'tab';
    var icon = type == 'icon';
    if(icon){
        var element = $(cursor).find('.'+name+':visible').parent();
        if (element.length == 0) element = $(cursor).find('a[title='+name+']');
    }
    else if(tab){
        element = $(cursor).find('.nav-tabs').find( "a:visible:contains('"+name+"')" ).first();
    } else {
        if (element.length == 0 && (link || button)) element = $(cursor).find("button:visible:contains('" + name + "'), button[name='" + name + "']").first();
        if (element.length == 0 && (link || button)) element = $(cursor).find("a:visible:contains('" + name + "'), a[name='" + name + "']").not($('.main-menu').find('a')).first();
        if (element.length == 0 && menu) element = $(cursor).find('.main-menu').find("a:visible:contains('" + name + "')").first();
    }

    if(recursively(element)){
        return click(name, type);
    } else {
        if (window['display_fake_mouse']) {
            function afterScrool() {
                function afterMoveMouse(){
                    element[index].click();
                }
                moveMouseTo(element[index], afterMoveMouse);
            }
            scroolToElement(element, afterScrool);
        } else {
            function afterScrool() {
                $("#fake-cursor").hide();
                element[index].click();
            }
            scroolToElement(element, afterScrool);
        }
    }
}

function clickMenu(name){
    return click(name, 'menu');
}

function clickLink(name){
    return click(name, 'link');
}

function clickTab(name){
    return click(name, 'link');
}

function clickButton(name){
    return click(name, 'button');
}

function clickIcon(name, index){
    return click(name, 'icon');
}

function lookAtPopupWindow(){
    cursor = $('#app_modal')[0]
}

function lookAt(text, only_panel){
    if(only_panel==true){
        var element = $(cursor).find(".panel-heading:visible:contains('"+text+"')").first();
        if (element.length == 0) element = $(cursor).find("h1:visible:contains('" + text + "')").first();
        if (element.length == 0) element = $(cursor).find("h2:visible:contains('" + text + "')").first();
        if (element.length == 0) element = $(cursor).find("h3:visible:contains('" + text + "')").first();
        if (element.length == 0) element = $(cursor).find("h4:visible:contains('" + text + "')").first();
    } else {
        var element = $(cursor).find("tr:visible:contains('" + text + "')");
        if (element.length == 0) element = $(cursor).find("p:visible:contains('" + text + "')").first();
        if (element.length == 0) element = $(cursor).find("div:visible:contains('" + text + "')").first();
    }
    if(recursively(element)){
        lookAt(text, only_panel);
    }
    else{
        cursor = element[0];
    }
}

function lookAtPanel(text){
    return lookAt(text, true);
}

function enter(name, value, submit){
    if(String(value)!='null' && String(value)){
        var element = $(cursor).find( "input[name='"+name+"'], textarea[name='"+name+"']" ).not("input[type='checkbox']").first();
        if (!element[0]) element = $(cursor).find( "label:contains('"+name+"')" ).parent().find('input, textarea').not("input[type='checkbox']").first();
        $('input[name=hidden-upload-value]').remove();
        if(element.prop("type")=='file'){
            $('<input type="hidden" name="hidden-upload-value" value="'+element[0].id+':'+value+'">').appendTo(document.body);
            return element;
        }

        if(recursively(element)){
            return enter(name, value, submit);
        } else {
            function afterScrool() {
                element.focus();
                if (window['display_fake_mouse']) {
                    fakeType(element, value, 0);
                } else {
                    element.val(value);
                    var daterangepicker = element.data('daterangepicker');
                    if(daterangepicker){
                        setTimeout(function(){daterangepicker.hide()}, 500);
                    }
                }
                element.focus();
                if (submit) typeReturn(element);
            }
            scroolToElement(element, afterScrool);
            return element;
        }
    }
}

function check(value){
    if(value==null){
        var element = $(cursor).find('input[type=checkbox]');
        if(recursively(element)){
            return check();
        } else {
            element.trigger('click');
        }
    } else {
        var checkbox = $(cursor).find("tr:contains('" + value + "')").parent().find('input[type=checkbox]');
        if (checkbox.length == 0) checkbox = $('.panel-heading:contains(' + value + ')').find('input[type=checkbox]');
        if (checkbox.length > 0) {
            function callback() {
                checkbox.trigger('click');
            }

            return scroolToElement(checkbox, callback);
        }
    }
}

function choose(name, value, headless){
    if(!value) return;

    var checkbox = $(cursor).find(".pick-value td:contains('"+value+"')" ).parent().find('input[type=checkbox]');
    if(checkbox.length>0){
        function callback(){
            checkbox.prop('checked', true);
        }
        return scroolToElement(checkbox, callback);
    }

    var element = $(cursor).find( "select[name='"+name+"']" );
    if (!element[0]) element = $(cursor).find( "label:contains('"+name+"')" ).parent().find('select');

    if(recursively(element)){
        return choose(name, value, headless);
    } else {
        if(headless){
            $(element).val(element.find("option:contains(" + value + ")").val());
        } else {
            element.select2("open");
            var $search = element.data('select2').dropdown.$search || element.data('select2').selection.$search;
            $search.val(value);
            $search.trigger('keyup');
            var lookup = "option:contains(" + value + ")";
            function waitValue() {
                var value = element.find(lookup).val();
                element.val(value).trigger('change');
                element.select2('close');
            }
            setTimeout(waitValue, '2000');
        }
        return element.parent()[0]
    }
}

function wait(ms){
    var start = new Date().getTime();
    var end = start;
    while(end < start + ms) {
      end = new Date().getTime();
   }
 }
