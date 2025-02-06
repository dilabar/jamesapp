from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission,BaseUserManager
import pytz

class Role(models.Model):
    """
    A Role represents a specific function or permission set for a user.
    Example roles: "Agency Admin", "Sub-account User"
    """
    name = models.CharField(max_length=255, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True, help_text="Permissions associated with this role")

    def __str__(self):
        return self.name

    def add_permission(self, permission):
        self.permissions.add(permission)

    def remove_permission(self, permission):
        self.permissions.remove(permission)

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        """
        if not email:
            raise ValueError("The email field must be set.")
        if not username:
            raise ValueError("The username field must be set.")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_agency(self, username, email, password, agency_name):
        """
        Create and return a new agency user with an associated AgencyAccount.
        """
        if not username:
            raise ValueError("The username must be provided")
        if not email:
            raise ValueError("The email must be provided")
        if not agency_name:
            raise ValueError("The agency name must be provided")

        # Create the agency user
        agency_user = self.create_user(
            username=username,
            email=self.normalize_email(email),
            password=password,
            user_type='agency',
        )

        # Create the associated AgencyAccount
        AgencyAccount.objects.create(
            agency=agency_user,
            agency_name=agency_name,
        )

        return agency_user
    def create_superuser(self, username, email, password=None, **extra_fields):
        """
        Create and return a superuser with elevated permissions.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    """
    Custom User model for Agency and Sub-Account users.
    """
    USER_TYPE_CHOICES = (
        ('agency', 'Agency'),
        ('sub_account', 'Sub Account'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='agency')
    parent_agency = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_accounts',
        help_text="The agency account that owns this sub-account. Null for agency users."
    )
    is_active = models.BooleanField(default=True)  # For account suspension feature
    objects = UserManager()  # Assign the custom manager
# Override related_name for groups and user_permissions
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
        related_query_name="custom_user",
    )
    roles = models.ManyToManyField(Role, blank=True, related_name='users', help_text="Roles assigned to the user")
    
    def add_role(self, role):
        self.roles.add(role)

    def remove_role(self, role):
        self.roles.remove(role)
        
    def is_agency(self):
        return self.user_type == 'agency'

    def is_sub_account(self):
        return self.user_type == 'sub_account'
    class Meta:
        permissions = [
            ("can_switch_accounts", "Can switch between sub-accounts"),
            ("can_manage_sub_accounts", "Can manage sub-accounts"),
        ]
    def get_all_subaccounts(self):
        """
        Get all subaccounts for this user if the user is an agency.
        Includes the user itself for easy querying.
        """
        if self.is_agency:
            # Assuming you have a way to link subaccounts to an agency (e.g., a `parent_agency` ForeignKey)
           return User.objects.filter(models.Q(parent_agency=self) | models.Q(id=self.id))

        return User.objects.filter(id=self.id)
class AgencyAccount(models.Model):
    """
    Agency account to store agency-specific information.
    """
    agency = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'agency'})
    agency_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ('can_manage_agency', 'Can manage agency accounts'),
        ]

    def __str__(self):
        return self.agency_name
    
class SubAccountProfile(models.Model):
    """
    Sub-account specific details.
    """
    
    sub_account = models.OneToOneField(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'sub_account'})
    assigned_roles = models.JSONField(default=dict)  # Store roles or permissions for sub-accounts
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Assuming phone number in E.164 format
    # Timezone validation using choices
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]
    timezone = models.CharField(
        max_length=100, 
        choices=TIMEZONE_CHOICES, 
        blank=True, 
        null=True
    )

    def has_role_permission(self, permission_name):
        roles = self.assigned_roles.get('roles', [])
        # Check if any role includes the required permission
        return permission_name in roles
    class Meta:
        permissions = [
            ('can_manage_sub_account', 'Can manage sub-accounts'),
        ]
    
    def __str__(self):
        return self.sub_account.username
    
class AccountSwitchLog(models.Model):
    """
    Log to track account switching by agencies.
    """
    agency = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'agency'})
    switched_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='switched_account')
    switch_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agency.username} switched to {self.switched_to.username} at {self.switch_time}"
# # Define the Agency model
# class Agency(models.Model):
#     name = models.CharField(max_length=100)
#     user = models.OneToOneField(User, on_delete=models.CASCADE)  # The agency is linked to a user (administrator)

#     def __str__(self):
#         return self.name

# # Define the Client/Subaccount model
# class Subaccount(models.Model):
#     agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="subaccounts")
#     name = models.CharField(max_length=100)
#     email = models.EmailField()
#     created_at = models.DateTimeField(auto_now_add=True)

#         # General Info Fields
#     address = models.CharField(max_length=255, blank=True, null=True)
#     city = models.CharField(max_length=100, blank=True, null=True)
#     phone_number = models.CharField(max_length=15, blank=True, null=True)  # Assuming phone number in E.164 format
#     # Timezone validation using choices
#     TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]
#     timezone = models.CharField(
#         max_length=100, 
#         choices=TIMEZONE_CHOICES, 
#         blank=True, 
#         null=True
#     )


#     def __str__(self):
#         return self.name

# # Define Role and Permissions (could use Django's built-in Groups and Permissions, but let's define custom ones for flexibility)
# class Role(models.Model):
#     name = models.CharField(max_length=50)
#     permissions = models.TextField()  # JSON or text-based permissions (e.g., "view_data", "edit_data")

#     def __str__(self):
#         return self.name

# # Define the Configuration model (CRM, Automations, etc.)
# class Configuration(models.Model):
#     subaccount = models.OneToOneField(Subaccount, on_delete=models.CASCADE, related_name="configuration")
#     crm_enabled = models.BooleanField(default=True)
#     automation_enabled = models.BooleanField(default=True)
#     user_limit = models.PositiveBigIntegerField(default=5)

#     def __str__(self):
#         return f"Configuration for {self.subaccount.name}"
