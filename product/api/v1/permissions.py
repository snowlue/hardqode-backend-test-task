from rest_framework.permissions import SAFE_METHODS, BasePermission


def make_payment(request):
    # TODO
    pass


class IsStudentOrIsAdmin(BasePermission):
    def has_permission(self, request, view):
        # TODO
        pass

    def has_object_permission(self, request, view, obj):
        # TODO
        pass


class ReadOnlyOrIsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff or request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or request.method in SAFE_METHODS
