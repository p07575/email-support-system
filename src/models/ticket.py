from datetime import datetime
from typing import Dict, Optional

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
            "ticket_id": self.ticket_id,
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
        ticket = cls(
            ticket_id=data["ticket_id"],
            from_email=data["from_email"],
            subject=data["subject"],
            message=data["message"],
            plain_message=data["plain_message"]
        )
        ticket.status = data.get("status", "received")
        ticket.received_at = data.get("received_at", datetime.now().isoformat())
        ticket.response = data.get("response")
        ticket.response_time = data.get("response_time")
        return ticket

# Global ticket queue
ticket_queue: Dict[str, Ticket] = {} 