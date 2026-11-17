
PLUGINEXT = so
# (console.so was listed here, but console.c never existed in this repo -> "No rule to make target")
PLUGINS = sample.$(PLUGINEXT) sig.$(PLUGINEXT) pid.$(PLUGINEXT) gui.$(PLUGINEXT)
COMMON_H = ../common/plugin.h ../common/cbasetypes.h

txt sql all: $(PLUGINS)

# [build] The output dir ../../plugins/ is not in the repo and nothing created it, so `make plugins`
# always failed ("cannot open output file ../../plugins/sample.so"). Order-only: create it first.
../../plugins:
	mkdir -p $@

# Shared objects need position-independent code (-fPIC); without it x86-64 ld refuses ("relocation
# R_X86_64_PC32 ... recompile with -fPIC"). sig needs a few common helpers: they are compiled into it
# from source with -fPIC, because the prebuilt ../common/obj/*.o are not PIC.
%.$(PLUGINEXT): %.c | ../../plugins
	$(CC) $(CFLAGS) -fPIC -shared -o ../../plugins/$@ $<

sig.$(PLUGINEXT): sig.c | ../../plugins
	$(CC) $(CFLAGS) -fPIC -DMINICORE -shared -o ../../plugins/$@ $< \
	../common/showmsg.c ../common/utils.c ../common/malloc.c

gui.$(PLUGINEXT): ../../plugins/gui.conf

../../plugins/%.conf: %.txt | ../../plugins
	cp -r $< $@

../../plugins/gui.conf: gui.txt

depend:
	makedepend -fGNUmakefile -o.$(PLUGINEXT) -Y. -Y../common *.c $(PLUGINS:%=../../plugins/%)
clean:
	rm -f *.o $(PLUGINS:%=../../plugins/%) GNUmakefile

# DO NOT DELETE

sample.$(PLUGINEXT): sample.c $(COMMON_H)
sig.$(PLUGINEXT): sig.c $(COMMON_H)
pid.$(PLUGINEXT): pid.c $(COMMON_H)
gui.$(PLUGINEXT): gui.c $(COMMON_H)
