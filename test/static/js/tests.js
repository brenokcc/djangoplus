var cursor = document;

function recursively(element){
    if(element.length==0 && cursor!=document) {
        if (cursor.parentNode != null) cursor = cursor.parentNode; else cursor = document;
        return true
    }
    return false
}

function scroolToElement(element){
    var obj = element[0];
    var curtop = 0;
    if (obj.offsetParent) {
        do {
            curtop += obj.offsetTop;
        }
        while (obj = obj.offsetParent);
        window.scroll(0, curtop - 300);
    }
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

    if (tab){
        element = $(cursor).find('.nav-tabs').find( "a:visible:contains('"+name+"')" );
    } else {
        if (element.length == 0 && (link || button)) element = $(cursor).find("button:visible:contains('" + name + "'), button[name='" + name + "']");
        if (element.length == 0 && (link || button)) element = $(cursor).find("a:visible:contains('" + name + "'), a[name='" + name + "']").not($('.main-menu').find('a'));
        if (element.length == 0 && menu) element = $(cursor).find('.main-menu').find("a:visible:contains('" + name + "')");
    }

    if(recursively(element)){
        return click(name, type);
    } else {
        scroolToElement(element);
        element[index].click();
    }
}

function clickMenu(name){
    return click(name, 'menu')
}

function clickLink(name){
    return click(name, 'link')
}

function clickTab(name){
    return click(name, 'link')
}

function clickButton(name){
    return click(name, 'button')
}

function clickIcon(name, index){

    if(index==null) index = 0;

    var element = $(cursor).find('.'+name+':visible').parent();
    if (element.length == 0) element = $(cursor).find('a[title='+name+']');

    if(recursively(element)){
        return clickIcon(name, index);
    } else {
        $(cursor).find(element[index]).click()
    }
}

function lookAtPopupWindow(){
    cursor = $('#app_modal')[0]
}

function lookAt(text, only_panel){
    if(only_panel==true){
        var element = $(cursor).find(".panel-heading:visible:contains('"+text+"')");
        if (element.length == 0) element = $(cursor).find("h1:visible:contains('" + text + "')");
        if (element.length == 0) element = $(cursor).find("h2:visible:contains('" + text + "')");
        if (element.length == 0) element = $(cursor).find("h3:visible:contains('" + text + "')");
        if (element.length == 0) element = $(cursor).find("h4:visible:contains('" + text + "')");
    } else {
        var element = $(cursor).find("tr:visible:contains('" + text + "')");
        if (element.length == 0) element = $(cursor).find("p:visible:contains('" + text + "')");
        if (element.length == 0) element = $(cursor).find("div:visible:contains('" + text + "')");
    }
    if(recursively(element)){
        lookAt(text, only_panel);
    }
    else{
        console.log(element);
        cursor = element[0];
    }
}

function lookAtPanel(text){
    return lookAt(text, true);
}

function enter(name, value, submit){

    if(String(value)!='null' && String(value)){
        var element = $(cursor).find( "input[name='"+name+"'], textarea[name='"+name+"']" )
        if (!element[0]) element = $(cursor).find( "label:contains('"+name+"')" ).parent().find('input, textarea')

        if(recursively(element)){
            return enter(name, value, submit);
        } else {
            element.focus();
            element.val(value);
            element.focus();
            scroolToElement(element);
            if (submit) typeReturn(element);
            return element
        }
    }
}

function choose(name, value, headless){
    var element = $(cursor).find( "select[name='"+name+"']" )
    if (!element[0]) element = $(cursor).find( "label:contains('"+name+"')" ).parent().find('select')

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