from django.contrib.auth.decorators import login_required


class LofinRequiredMixni(object):
    """定义一个类：目的为了重写as_view这个方法，让他拥有判断功能，而不再把验证空能卸载url中，而是对他进行了功能封装"""
    @classmethod
    def as_view(cls, **initkwargs):
        """封装一些页面需要判断是否登录"""
        view = super(LofinRequiredMixni,cls).as_view(**initkwargs)
        return login_required(view)