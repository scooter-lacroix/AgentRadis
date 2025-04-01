from app.tool.planning.planning import PlanningTool

def create_planning_tool(**kwargs):
    """
    Create and return a PlanningTool instance.
    
    Args:
        **kwargs: Keyword arguments to pass to the PlanningTool constructor.
        
    Returns:
        PlanningTool: A configured PlanningTool instance.
    """
    return PlanningTool(**kwargs)

