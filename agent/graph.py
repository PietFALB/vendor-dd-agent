from langgraph.graph import END, START, StateGraph

from agent import nodes
from agent.state import DDState


def build_graph():
    g = StateGraph(DDState)

    g.add_node("validate_input", nodes.validate_input)
    g.add_node("resolve_entity", nodes.resolve_entity)
    g.add_node("screen_sanctions", nodes.screen_sanctions_node)
    g.add_node("enhanced_review", nodes.enhanced_review)
    g.add_node("standard_review", nodes.standard_review)
    g.add_node("assess_risk", nodes.assess_risk)
    g.add_node("write_report", nodes.write_report)
    g.add_node("check_report", nodes.check_report)
    g.add_node("save_report", nodes.save_report)

    g.add_edge(START, "validate_input")
    g.add_conditional_edges(
        "validate_input",
        nodes.route_after_validate,
        {"continue": "resolve_entity", "stop": END},
    )
    g.add_edge("resolve_entity", "screen_sanctions")
    g.add_conditional_edges(
        "screen_sanctions",
        nodes.route_after_screening,
        {"enhanced": "enhanced_review", "standard": "standard_review"},
    )
    g.add_edge("enhanced_review", "assess_risk")
    g.add_edge("standard_review", "assess_risk")
    g.add_edge("assess_risk", "write_report")
    g.add_edge("write_report", "check_report")
    g.add_conditional_edges(
        "check_report",
        nodes.route_after_check,
        {"save": "save_report", "rewrite": "write_report"},
    )
    g.add_edge("save_report", END)

    return g.compile()
