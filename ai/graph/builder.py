from langgraph.graph import StateGraph, END

from graph.state import LegalChatState
from graph.nodes import (
    rag_node,
    extraction_node,
    anonymization_node,
    reasoning_node,
    formatter_node,
)


def build_legal_graph():
    graph = StateGraph(LegalChatState)

    graph.add_node("rag",           rag_node)
    graph.add_node("extraction",    extraction_node)
    graph.add_node("anonymization", anonymization_node)
    graph.add_node("reasoning",     reasoning_node)
    graph.add_node("formatter",     formatter_node)

    graph.set_entry_point("rag")
    graph.add_edge("rag",           "extraction")
    graph.add_edge("extraction",    "anonymization")
    graph.add_edge("anonymization", "reasoning")
    graph.add_edge("reasoning",     "formatter")
    graph.add_edge("formatter",     END)

    return graph.compile()


legal_graph = build_legal_graph()