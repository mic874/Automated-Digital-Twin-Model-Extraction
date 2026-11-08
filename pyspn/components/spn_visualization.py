from graphviz import Digraph
#import graphviz

#import os
#os.environ["PATH"] += os.pathsep + 'C:/Users/rc3000/AppData/Local/Programs/Python/Python312/Lib/site-packages/graphviz/' 

from .spn import *

def draw_spn(spn: SPN, file="data-knowledge-fused-model", show=True,
             print_place_labels=False, rankdir="TB",
             max_width_in=6.3, max_height_in=9.0):

    if rankdir == "TB":
        spn_graph = Digraph(engine="dot", graph_attr={'rankdir':'TB'})
    else:
        spn_graph = Digraph(engine="dot", graph_attr={'rankdir':'TB'})

    # draw places and marking
    place:Place
    for place in spn.places:
        if place.n_tokens == 0:
            if print_place_labels == True:
                spn_graph.node(place.label, shape="circle", label="", xlabel=place.label + "\n" + place.source, height="0.7", width="0.7", fixedsize="shape", fontsize="50", color=place.color, fontcolor=place.color)
            else: spn_graph.node(place.label, shape="circle", label="", height="0.7", width="0.7", fixedsize="shape", fontsize="50", color=place.color, fontcolor=place.color)
        else:
            if place.n_tokens < 5:
                lb = "<"
                for token_number in range(1, place.n_tokens+1):
                    lb = lb + "&#9679;"
                    if token_number % 2 == 0:
                        lb = lb + "<br/>"
                lb = lb + ">"
            else:
                lb = "{}".format(place.n_tokens)
            
            if print_place_labels == True:
                spn_graph.node(place.label, shape='circle', label=lb, xlabel=place.label + "\n" + place.source, height='0.7', width='0.7', fixedsize="shape", fontsize="50", color=place.color, fontcolor=place.color)
            else: spn_graph.node(place.label, shape='circle', label=lb, height='0.7', width='0.7', fixedsize="shape", fontsize="50", color=place.color, fontcolor=place.color)
        
    # draw transitions
    transition:Transition
    for transition in spn.transitions:
        #print("-----------", transition.label)
        if "loop" in transition.label.lower():
            #print("in here")
            label = ""
        elif "choice" in transition.label.lower():
            #print("in here")
            label = ""#"or-split"
        elif "join" in transition.label.lower():
            #print("in here")
            label = ""#"and-join"
        elif "split" in transition.label.lower():
            #print("in here")
            label = ""#"and-split"
        else:
            label = transition.label
        if transition.t_type == "T":
            print(transition.label)
            if rankdir == "TB" and transition.condition_label:
                spn_graph.node(transition.label, shape='rectangle', color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + transition.condition_label + "\n" + transition.source, height='0.3', width='0.7', fixedsize="shape", fontsize="50")
            elif rankdir == "TB" and transition.distribution != None and transition.distribution.keys() and str(list(transition.distribution.keys())[0]):
                spn_graph.node(transition.label, shape='rectangle', color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + str(list(transition.distribution.keys())[0]) + "\n" + transition.source, height='0.3', width='0.7', fixedsize="shape", fontsize="50")
            elif rankdir == "TB" and transition.distribution != None:
                spn_graph.node(transition.label, shape='rectangle', color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + str(list(transition.distribution.keys())[0]) + "\n" + transition.source, height='0.3', width='0.7', fixedsize="shape", fontsize="50")
            else:
                spn_graph.node(transition.label, shape='rectangle', color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + transition.condition_label + "\n" + transition.source, height='0.7', width='0.3', fixedsize="shape", fontsize="50")
        else:
            if rankdir == "TB" and transition.condition_label:
                spn_graph.node(transition.label, shape='rectangle', style='filled',  color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + transition.condition_label + "\n" + transition.source, height='0.3', width='0.7', fixedsize="shape", fontsize="50")
            elif rankdir == "TB" and transition.weight == 1:
                spn_graph.node(transition.label, shape='rectangle', style='filled', color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + transition.source, height='0.3', width='0.7', fixedsize="shape", fontsize="50")      
            elif rankdir == "TB" and transition.weight:
                spn_graph.node(transition.label, shape='rectangle', style='filled', color=transition.color, fontcolor=transition.color, label="", xlabel=label + "\n" + str(transition.weight) + "\n" + transition.source, height='0.3', width='0.7', fixedsize="shape", fontsize="50")
            else:
                spn_graph.node(transition.label, shape='rectangle', style='filled', color=transition.color, fontcolor=transition.color,  label="", xlabel=label + "\n" + str(transition.weight) + "\n" + transition.condition_label + "\n" + transition.source, height='0.7', width='0.3', fixedsize="shape", fontsize="50")

        input_arc:InputArc
        for input_arc in transition.input_arcs:
            if input_arc.multiplicity > 1:
                spn_graph.edge(input_arc.from_place.label, input_arc.to_transition.label, xlabel=str(input_arc.multiplicity), color=input_arc.color)
            else: spn_graph.edge(input_arc.from_place.label, input_arc.to_transition.label, color=input_arc.color)
        
        output_arc:OutputArc
        for output_arc in transition.output_arcs:
            if output_arc.multiplicity > 1:
                spn_graph.edge(output_arc.from_transition.label, output_arc.to_place.label, xlabel=str(output_arc.multiplicity), color=output_arc.color)
            else: spn_graph.edge(output_arc.from_transition.label, output_arc.to_place.label, color=output_arc.color)

        inhibitor_arc:InhibitorArc
        for inhibitor_arc in transition.inhibitor_arcs:
            if inhibitor_arc.multiplicity > 1:
                spn_graph.edge(inhibitor_arc.from_place.label, inhibitor_arc.to_transition.label, xlabel=str(inhibitor_arc.multiplicity), arrowhead="dot", color=inhibitor_arc.color)
            else: spn_graph.edge(inhibitor_arc.from_place.label, inhibitor_arc.to_transition.label, arrowhead="dot", color=inhibitor_arc.color)

    
    
    spn_graph.graph_attr.update({
        "dpi": "400",

        # Page fit: shrink the layout to this size (inches) if it is larger
        "size": f"{max_width_in},{max_height_in}",
        "ratio": "compress",

        # Narrow and tall: tight horizontally, generous vertically
        "nodesep": "0.45",
        "ranksep": "1.0",
        "pad": "0.2",
        "margin": "0.1",

        # Edge routing
        "splines": "polyline",
        "overlap": "false",
        "concentrate": "false",
        "outputorder": "edgesfirst",

        # Label positioning
        "forcelabels": "true"
    })

    spn_graph.node_attr.update({
        "margin": "0.1,0.1",
        "height": "0.4"
    })

    spn_graph.edge_attr.update({
        "labelfloat": "false",
        "labeldistance": "2.0",
        "labelangle": "25",
        "arrowsize": "1.5"
    })

    #spn_graph.render(
    #    filename="../output/models/data-knowledge-fused-model",
    #    format="png",
    #    view=False,
    #    cleanup=True
    #)

    spn_graph.save('../output/models/{}.gv'.format(file))
    
    
    spn_graph.render('../output/models/{}.gv'.format(file), view=False)

    #spn_graph.render(
    #filename='../output/models/{}.gv'.format(file),
    #format="svg",
    #view=False,
    #cleanup=True
    #)

    spn_graph.attr(dpi="400")

    spn_graph.format = "png"
    spn_graph.render(
        filename='../output/models/{}'.format(file),
        view=False,
        cleanup=True
    )

    #spn_graph.format = "pdf"

    #spn_graph.render('../output/models/{}.gv'.format(file), view=show)

    #spn_graph.render('../output/models/{}.gv'.format(file), view=show)

    #spn_graph.attr(dpi="400")

    #spn_graph.render('../output/models/data-knowledge-fused-model', view=False, format = "png", dpi=400)

    return spn_graph
