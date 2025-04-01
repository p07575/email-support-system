from datetime import datetime
from typing import Dict, Optional, List
from ..services.db_service import get_ticket, get_all_tickets, get_recent_tickets

class Ticket:
    def __init__(self, ticket_id: str, from_email: str, subject: str, message: str, plain_message: str):
        self.ticket_id = ticket_id
        self.from_email = from_email
        self.subject = subject
        self.message = message
        self.plain_message = plain_message
        self.status = "received"
        self.received_at = datetime.now().isoformat()
        self.response: Optional[str] = None
        self.response_time: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.ticket_id,
            "from_email": self.from_email,
            "subject": self.subject,
            "message": self.message,
            "plain_message": self.plain_message,
            "status": self.status,
            "received_at": self.received_at,
            "response": self.response,
            "response_time": self.response_time
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Ticket':
        """Create a Ticket instance from a dictionary (database record)"""
        ticket = cls(
            ticket_id=data["id"],
            from_email=data["from_email"],
            subject=data["subject"],
            message=data["message"],
            plain_message=data["plain_message"]
        )
        ticket.status = data.get("status", "received")
        ticket.received_at = data.get("received_at")
        ticket.response = data.get("response")
        ticket.response_time = data.get("response_time")
        return ticket

    @classmethod
    def get_by_id(cls, ticket_id: str) -> Optional['Ticket']:
        """Get a ticket by ID from the database"""
        ticket_data = get_ticket(ticket_id)
        if ticket_data:
            return cls.from_dict(ticket_data)
        return None
    
    @classmethod
    def get_all(cls) -> Dict[str, 'Ticket']:
        """Get all tickets from the database as a dictionary"""
        tickets_data = get_all_tickets()
        return {
            ticket["id"]: cls.from_dict(ticket) 
            for ticket in tickets_data
        }
    
    @classmethod
    def get_recent(cls, limit: int = 10) -> Dict[str, 'Ticket']:
        """Get recent tickets from the database as a dictionary"""
        tickets_data = get_recent_tickets(limit)
        return {
            ticket["id"]: cls.from_dict(ticket) 
            for ticket in tickets_data
        } 