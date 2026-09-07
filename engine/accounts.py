from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        # Existing users invite colleagues through Brightbean. No public signup.
        from apps.members.models import Invitation

        token = request.session.get("pending_invite_token")
        if not token:
            return False
        invite = Invitation.objects.filter(token=token, accepted_at__isnull=True).first()
        return bool(invite and not invite.is_expired)
