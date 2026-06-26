from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .system_agent import SystemAgent
from backend.authentication import JWTAuthentication
from accounts.permissions import IsAdmin

class ZModeExecutionView(APIView):
    """
    API View for triggering autonomous system execution in Z-Mode.
    Restricted to Admin users.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]
    
    def post(self, request):
        instruction = request.data.get('instruction')
        
        if not instruction:
            return Response({"error": "No instruction provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        agent = SystemAgent()
        result = agent.execute_instruction(instruction)
        
        return Response(result, status=status.HTTP_200_OK)
