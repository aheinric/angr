from .plugin import SimStatePlugin
from archinfo.arch_soot import SootAddressDescriptor, SootMethodDescriptor, SootAddressTerminator

import logging
l = logging.getLogger("angr.state_plugins.javavm_classloader")


class SimJavaVmClassloader(SimStatePlugin):
    def __init__(self, classes_loaded=None):
        super(SimJavaVmClassloader, self).__init__()
        self._classes_loaded = set() if classes_loaded is None else classes_loaded

    def load_class(self, class_):

        if self.is_class_loaded(class_):
            l.info("Class %s already loaded." % class_.name)
            return

        l.info("Load class %s \n\n" % class_.name)

        self.classes_loaded.add(class_.name)
        for method in class_.methods:
            if method.name == "<clinit>":
                l.info("Run initializer <clinit> ...")
                entry_state = self.state.copy()
                entry_state.callstack.ret_addr = SootAddressTerminator()
                simgr = self.state.project.factory.simgr(entry_state)
                simgr.active[0].ip = SootAddressDescriptor(SootMethodDescriptor.from_method(method), 0, 0)
                simgr.run()
                l.info("Run initializer <clinit> ... done \n\n")
                # The only thing that can change in the <clinit> methods are static fields so
                # it can only change the vm_static_table and the heap.
                # We need to fix the entry state memory with the new memory state.
                self.state.memory.vm_static_table = simgr.deadended[0].memory.vm_static_table.copy()
                self.state.memory.heap = simgr.deadended[0].memory.heap.copy()
                break

    def is_class_loaded(self, class_):
        return class_.name in self._classes_loaded

    def get_class(self, name):
        try:
            return self.state.project.loader.main_object.classes[name]
        except KeyError:
            return None
    
    def get_superclass(self, name):
        base_class  = self.get_class(name)
        if base_class:
            return self.get_class(base_class.super_class)
        return None

    def get_class_hierarchy(self, name):
        class_ = self.get_class(name)
        while class_:
            yield class_
            class_ = self.get_class(class_.super_class)


    @SimStatePlugin.memo
    def copy(self, memo):
        return SimJavaVmClassloader(
            classes_loaded=self.classes_loaded.copy()
        )

    @property
    def classes_loaded(self):
        return self._classes_loaded

# FIXME add this to a javavm preset
SimStatePlugin.register_default('javavm_classloader', SimJavaVmClassloader)