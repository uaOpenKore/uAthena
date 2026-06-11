
PLUGINEXT = so
PLUGINS = sample.$(PLUGINEXT) sig.$(PLUGINEXT) pid.$(PLUGINEXT) gui.$(PLUGINEXT) console.$(PLUGINEXT)
COMMON_H = ../common/plugin.h ../common/cbasetypes.h

txt sql all: $(PLUGINS)

%.$(PLUGINEXT): %.c
	$(CC) $(CFLAGS) -shared -o ../../plugins/$@ $<

sig.$(PLUGINEXT): sig.c
	$(CC) $(CFLAGS) -shared -o ../../plugins/$@ $< \
	../common/obj/showmsg.o ../common/obj/utils.o \
	../common/obj/minimalloc.o

gui.$(PLUGINEXT): ../../plugins/gui.conf

../../plugins/%.conf: %.txt
	cp -r $< $@

../../plugins/gui.conf: gui.txt

depend:
	makedepend -fGNUmakefile -o.$(PLUGINEXT) -Y. -Y../common *.c $(PLUGINS:%=../../plugins/%)
clean:
	rm -rf $(PLUGINS) GNUmakefile

# DO NOT DELETE

sample.$(PLUGINEXT): sample.c $(COMMON_H)
sig.$(PLUGINEXT): sig.c $(COMMON_H)
pid.$(PLUGINEXT): pid.c $(COMMON_H)
gui.$(PLUGINEXT): gui.c $(COMMON_H)
