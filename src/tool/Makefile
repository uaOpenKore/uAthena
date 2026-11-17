# [build] Real output files as targets (they were phony-named `adduser`/`convert`, so the tools rebuilt on
# every run), with their sources as prerequisites, and the output dir ../../tools/ created first: it is not
# in the repo and nothing created it, so `make tools` always failed ("cannot open output file").
all: ../../tools/adduser ../../tools/convert

../../tools:
	mkdir -p $@

../../tools/adduser: adduser.c | ../../tools
	$(CC) -o $@ adduser.c

../../tools/convert: convert.c | ../../tools
	$(CC) -o $@ convert.c

clean:
	rm -rf *.o ../../tools/adduser ../../tools/convert
