/* Buscar itens de menu */
String.prototype.removeAccents = function(){
 return this
         .replace(/[áàãâä]/gi,"a")
         .replace(/[éè¨ê]/gi,"e")
         .replace(/[íìïî]/gi,"i")
         .replace(/[óòöôõ]/gi,"o")
         .replace(/[úùüû]/gi, "u")
         .replace(/[ç]/gi, "c")
         .replace(/[ñ]/gi, "n")
         .replace(/[^a-zA-Z0-9]/g," ");
}

function initializeMenu(url, input_text, list_name, hide_ids, timeout){
    $('.second-level').css('display', 'none');
    $('.third-level').css('display', 'none');
    //selecting active menu
    if(url!='/' && $('aside').width()>90) {
        var url = '/breadcrumbs/reset' + url;

        var selector_first = ".first-level a[href^='" + url + "']";
        var parent_second = jQuery(".second-level").filter(function (index) {
            return jQuery("a[href^='" + url + "']", this).length >= 1;
        });
        parent_second.parent().children().show();
        var parent_third = jQuery(".third-level").filter(function (index) {
            return jQuery("a[href^='" + url + "']", this).length >= 1;
        });
        parent_third.parent().children().show();
        jQuery(selector_first).find('span').css('opacity', '0.6');
    }

    // Configuring menu search
    var list = jQuery(list_name);
    var new_list = list.clone().appendTo(list.parent());
    new_list.children().find('*').show();
    new_list.find('li.has-child').addClass("opened");
    new_list.hide();
    var input = jQuery(input_text);
    var keyTimeout;
    var lastFilter = '';

    // Default timeout
    if (timeout === undefined) {
        timeout = 200;
    }

    function filterList(ulObject, filterValue) {
        if (!ulObject.is('ul') && !ulObject.is('ol')) {
            return false;
        }
        var children = ulObject.children();
        var result = false;
        for (var i = 0; i < children.length; i++) {
            var liObject = jQuery(children[i]);
            if (liObject.is('li')) {
                var display = false;
                if (liObject.children().length > 0) {
                    for (var j = 0; j < liObject.children().length; j++) {
                        var subDisplay = filterList(jQuery(liObject.children()[j]), filterValue);
                        display = display || subDisplay;
                    }
                }
                if (!display) {
                    var text = liObject.text().removeAccents();
                    display = text.toLowerCase().indexOf(filterValue.removeAccents()) >= 0;
                    if (display) {
                        liObject.addClass('__show-children__');
                    }
                }
                liObject.css('display', display ? 'block' : 'none');
                result = result || display;
            }
        }
        ulObject.find('.__show-children__').find('*').show();
        return result;
    }

    input.change(function () {
        var hide_list = hide_ids.split(',');
        var filter = input.val().toLowerCase();
        if (filter != '') {
            list.hide();
            new_list.show();
            new_list.find('*').removeClass('__show-children__');
            hide_list.forEach(function (element, index, array) {
                jQuery(element).hide();
            });
        } else {
            list.show();
            new_list.hide();
            hide_list.forEach(function (element, index, array) {
                jQuery(element).show();
            });
        }
        filterList(new_list, filter);
        return false;
    }).keydown(function () {
        clearTimeout(keyTimeout);
        keyTimeout = setTimeout(function () {
            if (input.val() === lastFilter) return;
            lastFilter = input.val();
            input.change();
        }, timeout);
    });

    //Sidebar menu dropdown
    $('aside li').hover(
       function(){ $(this).addClass('open') },
       function(){ $(this).removeClass('open') }
    );

    //Collapsible Sidebar Menu
    $('.openable > a').click(function()	{
        if(!$('#wrapper').hasClass('sidebar-mini'))	{
            if( $(this).parent().children('.submenu').is(':hidden') ) {
                $(this).parent().siblings().removeClass('open').children('.submenu').slideUp();
                $(this).parent().addClass('open').children('.submenu').slideDown();
            }
            else	{
                $(this).parent().removeClass('open').children('.submenu').slideUp();
            }
        }
        return false;
    });

    //Toogle Menu
    $('#menuToggle').click(function()	{
        var action  = null;
        $('#wrapper').toggleClass('sidebar-hide');
        if($('#wrapper').hasClass('sidebar-hide')) action = 'hide';
        else action = 'show';
        $.get( "/admin/sidebar/"+action+"/", function( data ) {});
    });

    $('#sidebarToggle').click(function()    {
           $('#wrapper').toggleClass('sidebar-visible');
   });

    $(window).resize(function() {

    });

}
