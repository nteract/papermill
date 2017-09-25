#!/usr/bin/env bash
# cookbook filename: security_template

# Set a sane/secure path
PATH='/usr/local/bin:/bin:/usr/bin'
# It's almost certainly already marked for export, but make sure
\export PATH

# Clear all aliases. Important: leading \ inhibits alias expansion
\unalias -a
# Clear the command path hash
hash -r

# Set the hard limit to 0 to turn off core dumps
ulimit -H -c 0 --

# Set a sane/secure IFS (note this is bash & ksh93 syntax only--not portable!)
IFS=$' \t\n'

# Set a sane/secure umask variable and use it
# Note this does not affect files already redirected on the command line
# 022 results in 0755 perms, 077 results in 0700 perms, etc...
UMASK=022
umask $UMASK

until [ -n "$temp_dir" -a ! -d "$temp_dir" ]; do
    temp_dir="/tmp/meaningful_prefix.${RANDOM}${RANDOM}${RANDOM}"
done
mkdir -p -m 0700 $temp_dir \
    || (echo "FATAL: Failed to create temp dir '$temp_dir': $?"; exit 100)

# Do our best to clean up temp files no matter what
# Note $temp_dir must be set before this, and must not change!

cleanup="rm -rf $temp_dir"
trap "$cleanup" ABRT EXIT HUP INT QUIT
