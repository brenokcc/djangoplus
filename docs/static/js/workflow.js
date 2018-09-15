var graph = new joint.dia.Graph();
var roles = [];
var activities = [];
var activity = null;
var index = 0;
var indexY = 0;

function addRole(name){
    var fontSize = 16;
    if(name.length>28) fontSize = 12;
    var rect = new joint.shapes.basic.Rect({
        position: { x: (roles.length*200)+1, y: 5+1 },
        size: { width: 198, height: 28 },
        attrs: {
            rect: {
              stroke: '#FFFFFF'
            },
            text: {
                text: name,
                'font-size': fontSize,
                'font-weight': 'lighter',
                'font-variant': 'small-caps'
            }
        }
    });
    roles.push(name);
    activities[name] = [];
    graph.addCell(rect);
}

function addActivity(name, role){
    var name = name.substring(0, 45);
	var startDirection = 'bottom';
	var endDirections = 'top';
    var rect = new joint.shapes.basic.Rect({
        position: { x: 0, y: 0 },
        size: { width: 150, height: 70 },
        attrs: {
            text: {
                text: name.replace(' de', '_de').split(' ').join('\n').replace('_de', ' de'),
                'font-size': 12,
                'font-weight': 'lighter'
            }
        }
    });
    if(roles.indexOf(role)==-1) addRole(role);
    var currentIndex = roles.indexOf(role);
    var distance = currentIndex -index;
    var x = currentIndex*200;
    var y = activities[role].length*120;
    rect.translate(x+25, y+50);
    activities[role].push(name);
    var currentIndexY = activities[role].indexOf(name);
    var distanceY = currentIndexY - indexY;
    //console.log(name+' : '+distance+' , '+distanceY);
    graph.addCell(rect);
    if(index<roles.indexOf(role)){
        startDirection = 'bottom';
        endDirections = 'left';
    }
    if(index>roles.indexOf(role)){
        endDirections = 'top';
    }
    if(distance==1&&distanceY==0){
       startDirection = 'right';
       endDirections = 'left';
    }
    if(distance==-1&&distanceY==0){
       startDirection = 'left';
       endDirections = 'right';
    }
    if(activity!=null) connect(activity, rect, startDirection, endDirections);
    activity = rect;
    index = roles.indexOf(role);
    indexY = activities[role].indexOf(name);
}
var i = 1;
function connect(source, target, startDirection, endDirections){
    var rect = new joint.dia.Link({
        source: { id: source.id },
        target: { id: target.id },
        router: { name: 'manhattan', args: {startDirections: [startDirection], endDirections: [endDirections]}},
        connector: { name: 'rounded' },
        attrs: {
            '.connection': {
                stroke: '#333333',
                'stroke-width': 2
            },
            '.marker-target': {
                fill: '#333333',
                d: 'M 10 0 L 0 5 L 10 10 z'
            }
        },
        labels: [
            {
                attrs: {
                    text: {
                        text: i++,
                        fontFamily: 'sans-serif',
                        fontSize: 10
                    }
                },
                position: 0.7
            }
        ]
    });
    graph.addCell(rect);
}

function workflow(id, data){
    var containerId = 'workflow'+id;
    var containerSelector = '#'+containerId;
    var paperSelector = '#'+id;

    var dict=[];
    var count = 0;
    for(var i=0; i<data.length; i++){
        if(dict.indexOf(data[i].role)==-1){
            dict.push(data[i].role);
            dict[data[i].role] = 1
        } else {
            dict[data[i].role]+=1;
        }
        if(dict[data[i].role]>count){
            count = dict[data[i].role];
        }
    }

    var height = 40 + count * 120;
    var width = dict.length * 200;

    var paper = new joint.dia.Paper({
        el: $(paperSelector),
        width: width,
        height: height,
        gridSize: 10,
        model: graph,
        interactive : false
    });
    for(var i=0; i<data.length; i++){
        addActivity(data[i].activity, data[i].role);
    }
    var cols = '';
    for(var i=0; i<dict.length; i++) cols+='<td style="width: 200px"></td>';
    $("<table id='"+containerId+"'><tbody><tr>"+cols+"</tr></tbody></table>").insertBefore(paperSelector);
    //$("<table id='"+containerId+"'><thead><tr><td colspan='"+dict.length+"'>Visão Geral</td></tr><tr>"+cols+"</tr></thead><tbody><tr>"+cols+"</tr></tbody></table>").insertBefore(paperSelector);
    $(containerSelector).css('margin', 'auto').css('width', (width)+'px');
    $(containerSelector).find('td').css('border', 'solid 1px #000');
    //$(containerSelector).find('thead').find('tr').css('height', '30px').css('text-align', 'center');
    $(containerSelector).find('tbody').find('tr').css('height', height+'px');
    $(paperSelector).css('margin', 'auto').css('background', 'transparent');
    $(paperSelector).css('margin-top', '-'+(height+35)+'px');
    $(paperSelector).css('margin-bottom', '50px');
    $(paperSelector).find('.link-tools').css('display', 'none');
    $(paperSelector).find('.tool-remove').css('display', 'none');
    $(paperSelector).find('.marker-arrowhead').css('display', 'none');
}


data = [{activity:'Atividade A', role:'Administrador'},
{activity:'Atividade B', role:'Administrador'},
{activity:'Atividade A', role:'Pessoa'},
{activity:'Atividade D', role:'Pessoa'},
{activity:'Atividade E', role:'Secretário'},
{activity:'Atividade F', role:'Pessoa'},
{activity:'Atividade G', role:'Administrador'}]
//workflow(data);

