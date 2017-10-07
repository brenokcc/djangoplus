function classDiagram(id, data){
    var paperSelector = '#'+id;
    var graph = new joint.dia.Graph();
    var paper = new joint.dia.Paper({
        el: $(paperSelector),
        width: 800,
        height: 500,
        gridSize: 10,
        model: graph,
        interactive : false
    });

    var ids = [];
    var uml = joint.shapes.uml;
    for(var i=0; i<data.classes.length; i++) {
        var x = String(data.classes[i].position)[2] - 1;
        var y = String(data.classes[i].position)[0] - 1;
        var cls = new uml.Class({
            position: {x: x*275 + 50, y: y*150+50},
            size: {width: 150, height: 75},
            name: data.classes[i].name,
            attributes: [],
            methods: [],
            attrs: {
                '.uml-class-name-rect': {
                    fill: '#fff',
                    stroke: '#000',
                    'stroke-width': 1
                },
                '.uml-class-attrs-rect, .uml-class-methods-rect': {
                    fill: '#fff',
                    stroke: '#000',
                    'stroke-width': 1
                },
                '.uml-class-methods-text, .uml-class-attrs-text': {
                    fill: '#000'
                }
            }
        });
        ids[data.classes[i].name] = cls.id;
        graph.addCell(cls);

    }
    for(var i=0; i<data.compositions.length; i++){
        var a = ids[data.compositions[i][0]];
        var b = ids[data.compositions[i][1]];
        var ab = new uml.Composition({ source: { id: a }, target: { id: b }, router: { name: 'manhattan'},
        labels: [{ position: 0.25, attrs: { text: { text: data.compositions[i][2] } } }]});
        graph.addCell(ab);
    }
    for(var i=0; i<data.agregations.length; i++){
        var a = ids[data.agregations[i][0]];
        var b = ids[data.agregations[i][1]];
        var ab = new uml.Association({ source: { id: a }, target: { id: b }, router: { name: 'manhattan'},
        attrs: {'.marker-source': { fill: '#4b4a67', stroke: '#4b4a67', d: 'M 10 0 L 0 5 L 10 10 z'}},
        labels: [{ position: 0.75, attrs: { text: { text: data.agregations[i][2] } } }]});
        graph.addCell(ab);
    }
    //var ab = new uml.Composition({ source: { id: b.id }, target: { id: c.id }, router: { name: 'manhattan'}})
    //var ac = new uml.Aggregation({ source: { id: a.id }, target: { id: c.id }, router: { name: 'manhattan', args: {startDirections: ['right'], endDirections: ['left']}}})
    //graph.addCell(ab);
    //graph.addCell(ac);
    $(paperSelector).css('margin', 'auto');
    $(paperSelector).css('border', 'solid 1px #000');
    $(paperSelector).find('.link-tools').css('display', 'none');
    $(paperSelector).find('.tool-remove').css('display', 'none');
    $(paperSelector).find('.marker-arrowhead').css('display', 'none');
}