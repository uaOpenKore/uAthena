#include <stdio.h>
#include <time.h>
#include <unistd.h>
int main(void){ struct timespec a; for(int i=0;i<3;i++){ clock_gettime(CLOCK_MONOTONIC,&a); printf("%ld\n",(long)a.tv_sec); fflush(stdout); sleep(1);} return 0; }
