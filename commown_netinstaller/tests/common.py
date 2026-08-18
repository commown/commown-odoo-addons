class NetinstallMixin:
    @classmethod
    def lref(cls, ref):
        return cls.env.ref("commown_netinstaller." + ref)
