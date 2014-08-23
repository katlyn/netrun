#!/usr/bin/perl -Tw
# NetRun CGI Script: for ABET, dump a directory full of .sav files
#  Orion Sky Lawlor, olawlor@acm.org, 2005-2006 (Public domain)

use strict;

require "./util.pl";
BEGIN { require "./config.pl"; }

use Sys::Syslog;
openlog 'netrun_run', '', 'local1';        # don't forget this

#use CGI qw/:standard -nosticky/;
#use CGI qw/:standard/;
use CGI;

our $q = new CGI;
$q->param(); # Check for CGI errors early...
my $error = $q->cgi_error;
if ($error) { err("Error '$error' in CGI headers!"); }

# The user is taking this (single-line) action--record it.
sub journal {
	my $action="$ENV{'REMOTE_USER'} ".shift;
	my $date=`date '+%Y_%m_%d_%H_%M_%S'`;  # or localtime time
	chomp($date);
	my $info="ip '".$ENV{'REMOTE_ADDR'}."' port '".$ENV{'REMOTE_PORT'}."' agent '".$ENV{'HTTP_USER_AGENT'}."'";
	my $log="$action $date $info\n";
	open J,">>journal";
	print J $log;
	close J;
	#system("echo '$log' >> journal");
}

# from http://www.perl.com/pub/a/2002/10/01/hashes.html
  # Return the hashed value of a string: $hash = perlhash("key")
  # (Defined by the PERL_HASH macro in hv.h)
sub perlhash
  {
      my $hash = 0;
      foreach (split //, shift) {
          $hash = int($hash*33 + ord($_))&0x00ffffff;  # <- OSL modified
      }
      return $hash;
  }

# untaint this (tainted) string for use inside a single-quoted string
sub untaint_singlequote
{
	my $str=shift;
	if ($str =~ /^([\w\s~'"!#\$@%\^&*\(\)\{\}_\-+=\]\[\|\\\/:;<>,\.?]*)$/) {
		$str=$1; # Looks OK-- untaint it.
	} else {
		my_security("Single-quoted string '$str' contains invalid characters");
	}
	$str =~ s/'/'\\''/g; # quote out all the single quotes
	$str =~ s/\r//g; # get rid of annoying carriage-returns...
	return $str;
}

############## Setup
# Parse a few parameters before doing anything else:
my $rel_url=$q->url(-relative=>1);
if (length($rel_url)>5) { $rel_url="run"; }
my $script_url="$config::url_dir/$rel_url";

my $user="$ENV{'REMOTE_USER'}";
if (!$user) {$user="commandlinetest";} # For testing on the command line
if ($user =~ /^(\w[\w.]+)$/ ) {
	$user = $1; # Untaint
} else {
	my_security("User name '$user' contains invalid characters");
}
my $userdir="$config::run_dir/run/$user/";
my_mkdir($userdir);
chdir($userdir);

# Download a problem tarball:
my $tarball=$q->param('tarball');
if ($tarball) {  
	if ($tarball =~ /^(\w[\w.+-]+)$/ ) {
		$tarball = $1; # Untaint
	} else {
		my_security("Tar name '$tarball' contains invalid characters");
	}
	print $q->header(-type  =>  'application/octet-stream',
		-content_disposition => "attachment; filename=$tarball.tar");
	system("cat","project.tar");
	journal("downloading $tarball");
	exit(0);
}

# Download a tarball of all saved files
my $tarballA=$q->param('tarballA');
if ($tarballA) { 
	print $q->header(-type  =>  'application/octet-stream',
		-content_disposition => "attachment; filename=netrun_all.tar.gz");
	system("ln -fs ../../bin bin");
	system("tar czf - bin/run.cgi bin/config.pl bin/util.pl saved");
	journal("download_all");
	exit(0);
}

# Display a computed image (jpeg)
my $imgdisp=$q->param('imgdisp');
if ($imgdisp) { # Display the last-saved jpeg image
	print $q->header(-type => 'image/jpeg');
	journal("display_image");
	exec("cat","last.jpg");
	exit(0);
}

# Dump grade information (READ ONLY)
my $grades=$q->param('grades');
if ($grades) {
	if ($grades =~ /^(\w[a-zA-Z0-9\/_]+)$/ ) {
		$grades = $1; # Untaint
	} else {
		my_security("Grades name '$grades' contains invalid characters");
	}
	journal("dump_grades $grades");
	print $q->header(-type  =>  'text/html');
	if (-r "grades/$grades" ) {
		system("cat","grades/$grades");
		exit(0);
	} else { # Not found
		my_errlog("Grading file $grades not found","Referer=$ENV{'HTTP_REFERER'}");
		exit(0);
	}
}

############# Output HTML
print $q->header;

print $q->start_html(-title=>'NetRun',
		-script=>"
//  NetRun script support.  Dr. Orion Lawlor, olawlor\@acm.org, 2005/10
// Click-on, click-off check_input checkbox:
function updateButton(pageItem) {
        div=document.getElementById('div_'+pageItem);
        but=document.getElementById('check_'+pageItem);
        if (but.checked) {div.style.display='block';}
        else {div.style.display='none';}
}

// Automatic 'Code to run:' textarea resizing:
// Adapted by Dr. Lawlor from: http://tuckey.org/textareasizer/
function getDisplayLines(strtocount) {
    var hard_lines = 0; // newline count
    var last = 0; // character index
    while ( true ) {
        last = strtocount.indexOf('\\n', last+1); // find next newline
        if ( last == -1 ) break; // no more newlines
        hard_lines ++;
    }
    var soft_lines = Math.round(strtocount.length / 80); // wrapped
    var lines = hard_lines+2;
    if ( soft_lines > lines ) lines = soft_lines;
    var max_lines=24; // FIXME: adjustable max size?
    if ( lines > max_lines ) lines = max_lines; 
    return lines;
}
function resizeForm() {
    var the_form = document.forms[0];
    for ( var x in the_form ) {
        if ( ! the_form[x] ) continue;
        if( typeof the_form[x].rows != 'number' ) continue;
        the_form[x].rows = getDisplayLines(the_form[x].value);
    }
    //setTimeout('resizeForm();', 500); // Makes firefox use CPU time continually!
}

//Tabs courtesy of Alex Ross, in turn from
// http://www.alexking.org/blog/2003/06/02/inserting-at-the-cursor-using-javascript/
function insertAtCursor(myField, myValue) {
   if (document.selection) {
      myField.focus();
      var sel = document.selection.createRange();
      sel.text = myValue;
   }
   else if (myField.selectionStart || myField.selectionStart == '0') {
      var startPos = myField.selectionStart;
      var endPos = myField.selectionEnd;
      myField.value = myField.value.substring(0, startPos) + myValue + myField.value.substring(endPos, myField.value.length);
      /* Don't let value change mess with cursor... */
      myField.selectionStart = myField.selectionEnd = endPos+1;
   } else {
      myField.value += myValue;
   }
}

// Insert tab into textbox everywhere;
//  also intercepts the tab character on IE.
function InsertTab(obj,e) {
   //alert('InterceptTab called with '+e.keyCode);
   if (e.keyCode ==13) { resizeForm(); }
   if (e.keyCode == 9) { // catch tab.
      //alert('InterceptTabs caught a tab');
      insertAtCursor(obj, '	');
      e.cancelBubble = true; // IE....
      return false;
   }
   return true;
}
// Disables tabs on Mozilla & other DOM browsers; 
//   never even gets called on IE (where onkeypress doesn't work with tabs)
function EatTab(obj,e) {
   //alert('EatTab called with '+e.keyCode+' which '+e.which);

   if (e.keyCode ==13) { resizeForm(); }
   if (e.keyCode == 9) { // catch tab.
      if (e.stopPropogation) e.stopPropogation();
      return false;
   }
   return true;
}

function startupCode() {
	updateButton('input');
	updateButton('options');
	resizeForm();
}
",   ######### javascript ends here
		-onLoad=>"startupCode()",
		-style=>{'src'=>'style_default.css'});

# print $q->h1('UAF CS NetRun');



if ($rel_url eq "runa") { # ABET printing
 my $dir = $q->param('dir');
 if ($dir) {
  if ($dir =~ /^([\w]+[\w\/]*)$/) {
	$dir=$1; # Looks OK-- untaint it.
	foreach my $hw (<$userdir/saved/$dir/*.sav>) {
		&load_file($hw);
		&print_main_form();
		&compile_and_run();
		&print_end_form();
	}
  }
 }
}


print $q->start_form(-action=>$script_url,-autocomplete=>"off"); 
# autoComplete (e.g., LastPass) overwrites your new code with old code.
# POST-style always works, but not bookmarkable.
# print $q->start_form("GET"); # Bookmarkable, but doesn't work for long code...


# Load up CGI parameters from this .sav file: load_file("saved/foo.sav");
sub load_file {
	my $src=shift;
	open FILE,"<","$src" or my_security("File name '$src' does not exist");
	$q=new CGI(*FILE);
	close(FILE);
}
# Print a link to this saved file name: print "Try out ".saved_file_link("Testing");
sub saved_file_link {
	my $f=shift;
	return '<a href="'.$rel_url.'?file='.$f.'">'.$f.'</a>';
}

# File input
my $file=$q->param('file');
if ($file) {  # "file" mode: Loading up a saved input file
	if ($file =~ /^(\w[\w.+-]+)$/ ) {
		$file = $1; # Untaint
	} else {
		my_security("File name '$file' contains invalid characters");
	}
	print("Loading from file '$file'<br>\n");
	load_file("saved/$file.sav");
} 

if ($q->param('code')) {  # Has code already:
	if (!$q->param('foo_ret')) { # No explicit return type yet: set it
		$q->param('foo_ret','int'); # default to int, for pre-2014-08 backward compat
		$q->param('foo_arg0','void'); # default
	}
}

# Return a checked, untainted homework field number, like 2006_CS301/HW1/1
sub checkhwnum() {
	my $hw=$q->param('hwnum');
	if (!$hw) {return "";}
	if ($hw =~ /^([\w]+[\w\/]+)$/ ) {
		return $1; # Untaint
	} else {
		my_security("Homework field '$hw' contains invalid characters");
	}
}

# Howework load
my $hw=$q->param('hw');
if ($hw) {  # "hw" mode: Loading up a homework assignment
	if ($hw =~ /^(\w[\w+-\/]+)$/ ) {
		$hw = $1; # Untaint
	} else {
		my_security("Homework name '$hw' contains invalid characters");
	}
	print("Loading homework '$hw'\n");
	load_file("class/$hw.sav");

	# Stash the homework number in a hidden "hwnum" field.  This isn't ideal, frankly.
	$q->param('hwnum',$hw);

	my $name=$q->param('name');
	if ( -r "saved/$name.sav" ) {
	# Already have a saved homework with this name!  Rename the *new* one
		my $f=$name;
		$name=$name."_again";
		$q->param('name',"$name");
		print(", with bogus name '$name'.  I did not overwrite your 
previous attempt, which is still called '".saved_file_link($f)."'");
	}

	print("<br>");
} 




&print_main_form();

if ($q->param('code')) { &compile_and_run(); }

&print_end_form();




print "<ul>\n";

# Make list of saved files
print "<li>Saved files: <ul>\n";
my $prevpre="notreallyaprefix";
foreach my $file (<$userdir/saved/*.sav>) {
    if ( $file =~ s/(\w[\w.+-]+).sav$//g ) {
        my $f=$1;
	my $pre=$f;
	$pre =~ s/[._].*//g;
        if ($pre ne $prevpre) { # Start a new row with each new prefix
		print "<li>$pre:  ";
		$prevpre=$pre;
	}
	print saved_file_link($f)."\n";
    }
}
print "</ul>\n";

# Print out one homework assignment
sub print_hw {
    $hw=shift;
    my $hw_short=endname($hw);
    print "<li><a name=\"$hw_short\">".endname($hw);
    $hw =~ m/(.*)/; $hw=$1;
    my $info="$hw/info.html";
    if (-r $info) {print(" ".my_cat($info)."<br>\n");}
    print " Problems: ";
    foreach my $prob (<$hw/*\.sav>) {
      $prob =~ m/class\/([\w\/]*)\.sav/;
      my $hwnum = $1;  
      $prob =~ m/([\w]+)\.sav$/;
      $prob=$1;
      print "\n".'<a href="',$rel_url,'?hw=',$hwnum,'">',$prob,"</a>";
      my $hw_und=slash_to_underscore($hwnum);
      if ( -r "hw/$hw_und" ) { print ' OK! &nbsp; '; }
    }
}

# Make list of homework assignments
foreach my $class (reverse <$userdir/class/*>) {
  if ($class =~ m/($userdir\/class\/[\w\/]*)/ ) {
    $class = $1;
  } else { my_security("Class directory $class invalid!");}
  print "\n<li>".my_cat("$class/info.html")."\n<ul>\n";
  if ($rel_url eq "runt") {
   foreach my $hw (reverse <$class/tHW*>) {
      print_hw($hw);
    }
   foreach my $hw (reverse <$class/tL*>) {
      print_hw($hw);
    }
  }
  foreach my $hw (reverse <$class/HW*>) {
    print_hw($hw);
  }
  foreach my $hw (reverse <$class/L*>) {
    print_hw($hw);
  }
  foreach my $hw (reverse <$class/[0-9]*>) {
    print_hw($hw);
  }
  if ( -d "$class/Example" ) {print_hw("$class/Example");}
  print "</ul>\n";
}
print "</ul>\n";



print '<p><a href="help.html">NetRun Help</a> and <a href="examples.html">Examples</a>';

if ($q->param('name')) {
  print '<p><a href="'."$rel_url?tarball=".$q->param('name').'">Download this file as a .tar archive</a>';
}
  print '<p><a href="'."$rel_url".'?tarballA=1">Download all saved files as a big .tar.gz archive</a>';

# Make it possible for me to save runs as a big URL...
if ($q->param()) {
	my $url="$config::url_dir/run?" .
		'name='."Testing". #  uri_escape($q->param('name')). # Don't overwrite...
		&param_to_cgiarg('code').&param_to_cgiarg('lang').
		&param_to_cgiarg('mach').&param_to_cgiarg('mode').
		&param_to_cgiarg('input').&param_to_cgiarg('check_input').
		&param_to_cgiarg('linkwith').
		&param_to_cgiarg('foo_ret').&param_to_cgiarg('foo_arg0').
		&param_to_cgiarg('orun'). &param_to_cgiarg('ocompile');
	if ($rel_url eq "runt") { # Lecture-notes copy-and-pastable version
		use HTML::Entities; # <- needed for printable HTML
		print '<hr>Code as run:<pre>'.encode_entities($q->param('code')).'</pre><p><a href="',$url,'">(Try this in NetRun now!)</a>';
	} elsif (length($url) < 8000) { # Fits in one URL 
		print '<p><a href="',$url,'">Bookmarkable Code URL (as run)</a>';
	}
}

print
	$config::end_page;

# Convert a CGI parameter to a CGI argument.
sub param_to_cgiarg {
	use URI::Escape;
	my $argname=shift;
	my $ret="";
	foreach my $arg ($q->param($argname)) { 
		$ret .= "&$argname=" . uri_escape($arg); 
	}
	return $ret;
}


########################### main_form ##############################
sub print_main_form {
	print
		'<TABLE BORDER=1><TR><TD VALIGN=top COLSPAN=2>',"\n";

	print
		'<DIV STYLE="width: 46em"><TABLE BORDER=0 WIDTH=100%><TR><TD>Run name:    ',
		$q->textfield(-name=>'name',-default=>"Testing"),
		"\n</TD><TD align=right>UAF CS NetRun</TD></TR></TABLE> \n";

	if ($rel_url eq "runh") { # Homework prep:
		print "Homework: ",$q->textfield(-name=>'hwnum',-default=>"2010_CSXXX/tHWY/Z"),"<br>\n";

		my $hwfile="instructor/".checkhwnum();
		my $hwdir=$hwfile; 
		$hwdir =~ m/(.*)\/[0-9]+/; $hwdir=$1;
		print "Checking for homework dir '$hwdir'...<br>\n";
		if (-d $hwdir) { # Dump homework info to files:
			open(HTML,">$hwfile.html") or err("Cannot create $hwfile.html");
                        print HTML $q->param("hwhtml");
                        close HTML;

			open(SAV,">$hwfile.sav") or err("Cannot create $hwfile.sav");
			$q->save(*SAV);
                        close SAV;

			open(GRD,">$hwfile.grd") or err("Cannot create $hwfile.grd");
			print GRD "#!/bin/sh\n. netrun/grade_util.sh\n\n";
                        my $i=1;
			while ($q->param("gradeout$i") && length($q->param("gradeout$i"))>0) {
				print GRD "in='".untaint_singlequote($q->param("gradein$i"))."'\n";
				print GRD "out='".untaint_singlequote($q->param("gradeout$i"))."'\n";
				print GRD "grade_prog\n\n";
				$i=$i+1;
			} 
			print GRD "grade_done\n";
                        close GRD;
			chmod 0755,"$hwfile.grd"
		}
	}

	
	if ($q->param('hwnum')) {
	# They're trying to solve a homework here.
		my $hwnum=checkhwnum();
		if (-e "class/$hwnum.html") {
		# Print out the homework description
		print "$hwnum Homework Instructions: ".my_cat("class/$hwnum.html")."<br>\n";
		}
	}

	if ($rel_url eq "runh") { # Homework prep:
		print "Problem Instructions (HTML):<br></DIV>\n",
			$q->textarea(-name=>'hwhtml',-columns=>85,-rows=>4,
				-onkeydown=>"javascript:return InsertTab(this,event);", 
				-onkeypress=>"javascript:return EatTab(this,event);", 
				-default=>"For this problem, you should...");
		print "<br>Grading prefix code:<br>\n",
			$q->textarea(-name=>'gradecode',-columns=>85,-rows=>3,
				-onkeydown=>"javascript:return InsertTab(this,event);", 
				-onkeypress=>"javascript:return EatTab(this,event);");
		print "<br>Student's default code:<br>\n ",
			$q->textarea(-name=>'code',-columns=>85,-rows=>3,
				-onkeydown=>"javascript:return InsertTab(this,event);", 
				-onkeypress=>"javascript:return EatTab(this,event);" 
			),"\n";
		print "<br>Grading suffix code:<br>\n",
			$q->textarea(-name=>'gradepost',-columns=>85,-rows=>3,
				-onkeydown=>"javascript:return InsertTab(this,event);", 
				-onkeypress=>"javascript:return EatTab(this,event);");
		
	} else {
		# Preserve the hidden homework fields...
		if ($q->param('hwnum')) {print $q->hidden('hwnum',$q->param('hwnum'));}
		if ($q->param('gradecode')) {print $q->hidden('gradecode',$q->param('gradecode'));}
		if ($q->param('gradepost')) {print $q->hidden('gradepost',$q->param('gradepost'));}
		
		# Format the code area
		my $numrows=3;
		if ($q->param('code')) {
			my @rows=split("\n",$q->param('code'));
			$numrows=1+scalar(@rows);
			my $numrowsmax=30;
			if ($numrows>$numrowsmax) {$numrows=$numrowsmax;}
		}
		
		print	"Code to run:<br></DIV>\n ",
			$q->textarea(-name=>'code',-columns=>85,-rows=>$numrows,
				-onkeydown=>"javascript:return InsertTab(this,event);", 
				-onkeypress=>"javascript:return EatTab(this,event);" 
			),"\n";
	}

	print
		"</TD></TR><TR><TD VALIGN=top>\n";
	print '<div align=left><input type="submit" name="Run It!" value="Run It!" title="[alt-shift-r]" accesskey="r"  /></div>';
	
	print
		"<p>",
		$q->checkbox_group(-name=>'check_input',
			-values=>["Input"],
			-id=>"check_input",
			-onClick=>"updateButton('input')",
			-attributes=>{-title=>"[alt-shift-i]",-accesskey=>"i"});

	print '<div id="div_input" style="display:none">',
		$q->textarea(-name=>"input",-rows=>4,-columns=>30),
		'</div>';
	
	
	print
		"<p>",
		$q->checkbox_group(-name=>'check_options',
			-values=>["Options"],
			-id=>"check_options",
			-onClick=>"updateButton('options')");
	print '<div id="div_options" style="display:none;">';
	
	print
		"<p>Language:",
		$q->popup_menu(-name=>'lang',
			-values=>[
			'C++',
			'C++0x',
			'C',
			'Assembly-NASM',
			'Assembly',
			'Fortran 77',
			'OpenMP',
			'MPI',
			'CUDA',
			'GPGPU',
			'OpenCL',
			'Python',
			'Python3',
			'Perl',
			'PHP',
			'JavaScript',
			'Ruby',
			'Bash',
			'Prolog',
			'glfp',
			'glsl',
			'funk_emu',
			'spice',
			'vhdl'],
			-labels=>{'Assembly' => 'Assembly-GNU',
				'glfp' => 'OpenGL Fragment Program',
				'glsl' => 'OpenGL Shader Language (GLSL)',
				'spice' => 'SPICE Analog Circuit',
				'C++0x' => 'C++11',
				'vhdl' => 'VHDL Digital Circuit'},
			-default=>['C++']),"\n";

	print
		"<p>Mode:",
		$q->popup_menu(-name=>'mode',
			-values=>['frag','file','main'],
			-labels=>{
				'frag' => 'Inside a Function',
				'file' => 'Whole Functions (file)',
				'main' => 'Whole Program (main)'
			},
			-default=>['frag']),"\n";

	print   "<p>Function: ",
		$q->popup_menu(-name=>'foo_ret',
			-values=>['void','long','int','double','float','std::string'],
			-default=>['long']),
		" foo(",
		$q->popup_menu(-name=>'foo_arg0',
			-values=>['void','long','int','double','float','std::string'],
			-default=>['void']),
		")\n";

	print
		"<p>Machine:",
		$q->popup_menu(-name=>'mach',
			-values=>[
				'x64',
				'sandy64',
				'phenom64',
				'x86_2core',
				'x86',
			#	'x86_atom',
			#	'x86_4core',
			#	'ia64',
				'win32',
				'x86_2',
				'486',
			#	'Alpha',
				'ARM',
				'SPARC',
				'MIPS',
				'PPC',
			#	'PPC_EMU',
				'PIC'
			],
			-labels=>{
				'x64' => 'x86_64 Q6600 x4',
				'sandy64' => 'x86_64 Sandy Bridge x4',
				'phenom64' => 'x86_64 Phenom II x6',
				'x86' => 'x86 P4 x2',
				'x86_atom' => 'x86 Atom x1',
				'x86_2core' => 'x86 Core2 x2',
			#	'x86_4core' => 'x86  (Linux)',
			#	'ia64' => 'ia64 (Itanium Linux)',
				'win32' => 'x86 (Windows) EMULATED',
				'x86_2' => 'x86 dual P3 (Linux)',
				'486' => '486 (Ancient Linux)',
			#	'Alpha' => 'DEC Alpha (NetBSD)',
				'ARM' => 'ARM (ARMv6 Linux)',
				'SPARC' => 'SPARC (Sun Ultra5 Linux)',
				'MIPS' => 'MIPS (SGI IRIX)',
				'PPC' => 'PowerPC (OS X)',
			#	'PPC_EMU' => 'PowerPC (Linux) EMULATED',
				'PIC' => 'PIC Microcontroller'
			},
			-default=>['x64']),"\n";

	print
		"<p>Compile options:",
		$q->checkbox_group(-name=>'ocompile',
			-values=>['Optimize','Debug','Warnings','Verbose','Shared'],
			-defaults=>['Optimize','Warnings']),"<br>\n";

	print
		"<p>Actions:",
		$q->checkbox_group(-name=>'orun',
			-values=>['Run','Disassemble','Grade','Time','Profile'],
			-defaults=>['Run','Grade']),"\n";

	print '<p>Link with: ',
		$q->textfield(-name=>"linkwith");

	if ($q->param('lang') eq "MPI") {
		print '<p>MPI Processes (1-20): ',
			$q->textfield(-name=>"numprocs");
	}

	print "<hr>";
	if (1) {
		print "Announcements:
	<UL>
		<li>Disqus comments for homeworks after OK! (2014-08-22)
		<li>foo can take or return long, string, etc.  (2014-08-20)
		<li>Keyboard shortcut: Alt-R runs it! (2012-09-28, thanks to Ben White)
	</UL>
	";
	}
	print "Version 2014-08-22";
	print "</div>";

	if ($rel_url eq "runh") { # Homework prep: store correct inputs and outputs
		my $i=0;
		do {
			$i=$i+1;
			print "<hr>Grading input $i:<br>",
				$q->textarea(-name=>"gradein$i",-rows=>2,-columns=>30);
			print "<br>Expected output $i:<br>",
				$q->textarea(-name=>"gradeout$i",-rows=>4,-columns=>30);
		} while ($q->param("gradeout$i") && length($q->param("gradeout$i"))>0);
	}

	print "</TD><TD VALIGN=TOP>";

	print $q->end_form;
}


sub print_end_form {
	print  $q->hr,"Finished.",
		'</TD></TR></TABLE>';
}



########################### compile_and_run ############################
## Compile and execute code.
sub compile_and_run {
	# Create project() file
	my $proj=create_project_directory();
	
	# Create a tarball
	system("tar cf project.tar project");

	# Run project remotely and write output to a file:
	my_start_redir('log'); 
	system("$config::run_dir/bin/sandsend",
		"-f","$userdir/project.tar",
		"-u","$user",
		"$proj->{sr_host}:$proj->{sr_port}") 
		and print("<h2>ERROR!</h2> Cannot send off project (machine may be down)\n<br>");
	my_end_redir();

	my $res=my_cat("log");	

	# if ($lang eq "glfp") { 
		separate_text_binary('log','last.jpg');
	# } else {
	# Print file to screen
	#	print $res;
	# }

	# Check for grading-OK message:
	my $hwnum = checkhwnum();
	if ( $hwnum && $res =~ m/GRADEVAL="@<YES!>&">/ ) {
		my $hw_und=slash_to_underscore($hwnum);
		journal("hwok $hw_und");
		system("cp","$proj->{src}","hw/$hw_und");
		
		
		print '<p>Now that you\'ve solved it, feel free to discuss the issues in this homework here:
    <div id="disqus_thread"></div>
    <script type="text/javascript">
        /* * * CONFIGURATION VARIABLES: EDIT BEFORE PASTING INTO YOUR WEBPAGE * * */
        var disqus_shortname = "netrun"; // required: replace example with your forum shortname
	var disqus_url = "https://lawlor.cs.uaf.edu/netrun/run?hw='.$hwnum.'";
        (function() {
            var dsq = document.createElement("script"); dsq.type = "text/javascript"; dsq.async = true;
            dsq.src = "//" + disqus_shortname + ".disqus.com/embed.js";
            (document.getElementsByTagName("head")[0] || document.getElementsByTagName("body")[0]).appendChild(dsq);
        })();
    </script>
    <noscript>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript">comments powered by Disqus.</a></noscript>
    <a href="http://disqus.com" class="dsq-brlink">comments powered by <span class="logo-disqus">Disqus</span></a>
';
	}
}


## Untaint this string, and make it like a project name
sub untaint_name {
	my $name=shift;
	if (!$name) { $name="Testing"; }

	# 'today' is the one writeable subdirectory (must be manually inserted in run/user/save)
	if ($name =~ /^today\/(\w[\w. +-]+)$/ ) {
		$name='today/'.$1; # untaint and put back
	} elsif ($name =~ /^(\w[\w. +-]+)$/ ) {
		$name = $1; # Untaint
	} else {
		my_security("Run name '$name' contains invalid characters");
	}

	# Replace spaces with underscores
	$name =~ s/ /_/g;
	return $name;
}

## Untaint this C/C++ type name, and return it
sub untaint_typename {
	my $t=$q->param(shift);
	
	if ($t =~ /^(\w[\w:._<>]*)$/ ) {
		$t = $1; # Untaint
	} else {
		my_security("Type name '$t' contains invalid characters");
	}

	return $t;
}

########################### create_project_directory ############################
## Build a Makefile and surrounding stuff for this project
sub create_project_directory {

# Extract out and security-check everything we need:
	my $code = $q->param('code');
	if (!$code) {print("You'll have to enter some code...\n"); return;}
	
	# Replace Microsoft curly quotes in code with normal ASCII quotes:
	$code =~ s/[\x93\x94]/\"/gs;
	# Replace /r/n with just /n:
	$code =~ s/[\r]//g;  # UNIX-ify newlines
	
	if ($code =~ /^([\w\s~'"!#\$@%\^&*\(\)\{\}_\-+=\]\[\|\`\\\/:;<>,\.?]+)$/) {
		$code=$1; # Looks OK-- untaint it.
	} else {
		my_security("Code '$code' contains invalid characters");
	}

	my $gradecode = $q->param('gradecode');
	if (!$gradecode) { $gradecode=""; }
	elsif ($gradecode =~ /^([\w\s~'"!#\$@%\^&*\(\)\{\}_\-+=\]\[\|\\\/:;<>,\.?]+)$/) {
		$gradecode=$1; # Looks OK-- untaint it.
	} else {
		my_security("Grade code '$gradecode' contains invalid characters");
	}
	my $gradepost = $q->param('gradepost');
	if (!$gradepost) { $gradepost=""; }
	elsif ($gradepost =~ /^([\w\s~'"!#\$@%\^&*\(\)\{\}_\-+=\]\[\|\\\/:;<>,\.?]*)$/) {
		$gradepost=$1; # Looks OK-- untaint it.
	} else {
		my_security("Grade post '$gradepost' contains invalid characters");
	}
	
	my $name=untaint_name($q->param('name'));
	
	my $mode=$q->param('mode');
	if (!$mode) { $mode="frag"; }
	if ($mode =~ /^([\w]+)$/ ) {
		$mode = $1; # Untaint
	} else {
		my_security("Run mode '$mode' contains invalid characters");
	}
	
	# lang and mach are checked for string match only
	my $lang=$q->param('lang');
	if (!$lang) { $lang="Assembly"; }
	my $mach=$q->param('mach');
	if (!$mach) { $mach="x86"; }
	
	my @ocompile=$q->param('ocompile');
	my @orun=$q->param('orun');
	#if (!@orun) { @orun=("Disassemble", "Run"); }		
# Done checking-- log and run the thing
	my $short_code;  # Syslog chokes on huge logs
	if (length($code)>=500) { $short_code=substr($code,0,500) . "...";}
	else {$short_code=$code;}
	journal("run $name len=".length($code)." hash=".perlhash($code));
	my_log("Running","user '$user' mach/lang '$mach/$lang' code '$short_code'");
	# print p,"User '$user' mach/lang '$mach/$lang' mode '$mode' run '$name'<br>";
	# print p,"Code: ",pre($code);
	
	my $srcext=""; # Extension of source code file
	my $srcpre=""; # Stuff to put before the user's code 
	my $srcpost=""; # Stuff to put after the user's code
	my $srcadd=""; # Stuff to link with the user's code
	my $toolpre=""; # Path to compiler & disassembler (& compiler prefix)
	my $compiler=""; # Name of tool used to create output
	my @cflags=(); # Flags passed to compiler
	my $linker="g++"; # Used to link output
	my @lflags=(); # Linker flags
	my $disassembler="objdump -drC -M intel"; # Disassembler
	my $main="main.obj"; # Prebuilt copy of main routine (for speed)
	my $sr_host="";  # Network target for build (needed outside)
	my $sr_port="2983";
	my $saferun="netrun/safe_run.sh";
	my $srcflag="-c";
	my $outflag="-o";
	my $netrun="netrun/obj";
	my $scriptrun='/home/netrun_scripting/chrootrun/chrootrun ';

	# Prepare build subdirectory
	system("rm","-fr","project");
	system("cp","-r","$config::run_dir/support/project","project");
	my $hwnum=checkhwnum();
	if ($hwnum) {
	# Is a homework-- try grading as well...
		system("cp","class/$hwnum.grd","project/netrun/grade.sh");
	}
	
	my $ret="int";
	my $arg0="void";
	my $proto="int foo(void)";
	if ($q->param('foo_ret')) {
		$ret=untaint_typename('foo_ret');
		$arg0=untaint_typename('foo_arg0');
		$proto="$ret foo($arg0)";
		push(@cflags,"-DNETRUN_FOO_DECL='".$proto."'");
	}

	if ($mode eq 'main') { $main=""; } # User will write main routine

	if (grep(/^Optimize$/, @ocompile)==1) {push(@cflags,"-O1");}
	if (grep(/^Debug$/, @ocompile)==1) {push(@cflags,"-g");}
	if (grep(/^Warnings$/, @ocompile)==1) {push(@cflags,"-Wall");}
	if (grep(/^Shared$/, @ocompile)==1) {push(@cflags,"-fPIC");}
	
	if (grep(/^Run$/, @orun)==1) {$netrun="$netrun netrun/run";}
	if (grep(/^Grade$/, @orun)==1) {$netrun="$netrun netrun/grade";}
	if (grep(/^Time$/, @orun)==1) {
		if ($mode eq 'main') {
			print "Sorry, cannot time a Whole Program; ";
			print "for the Time checkbox to work, you need to run inside a function, or write a foo function. <br>\n";
		}
		else {
			push(@lflags,"-DTIME_FOO=1");
			$main="lib/main.cpp"; # Must recompile main.cpp with timing enabled
		}
	}
	if (grep(/^Profile$/, @orun)==1) {
		push(@cflags,"-pg");
		push(@lflags,"-pg");
		$netrun="$netrun netrun/profile";
	}
	if (grep(/^Disassemble$/, @orun)==1) {$netrun="$netrun netrun/dis";}

###############################################	
# Language switch
	if ( $lang eq "C++" or $lang eq "C++0x" or $lang eq "OpenMP") {  ############# C++
		$compiler="g++";
		if (grep(/^Profile$/, @orun)!=1) { # -pg and -fomit don't work together
			push(@cflags,"-fomit-frame-pointer");
	        }
		if ($lang eq "OpenMP") {$compiler=$linker="g++-4.2 -fopenmp -msse3";}
		if ($lang eq "C++0x") {$compiler=$linker="g++-4.7 -fopenmp -msse3 -std=c++0x";}
		$srcext="cpp";
		$srcpre='/* NetRun C++ Wrapper (Public Domain) */
#include <cstdio>
#include <cstdlib>
#include <ctype.h>
#include <cstring>
#include <cmath>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <vector>
#include <map>
#include <string>
#include "lib/inc.h"
using namespace std; /* ONLY for 202 examples... */
//using std::cout; using std::cin; using std::endl; /* <- avoid annoyance; Gaddis textbook compatibility */

' . $gradecode;
		if ($mode eq 'main') { # whole program, with headers
			$srcpre=$gradecode;
		}
		if ($mode eq 'frag') { # Subroutine fragment
			$srcpre=$srcpre . $proto . " {\n";
			$srcpost="\n;";
			if ($ret ne "void") { $srcpost .= "\n  return 0;"; }
			$srcpost .= "\n}\n" . $gradepost;
		}
	}
	elsif ( $lang eq "C") { ############# C
		$compiler="gcc -fomit-frame-pointer"; 
		$srcext="c";
		$srcpre='/* NetRun C Wrapper (Public Domain) */
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>
#include <math.h>
#include "lib/inc.h"

' . $gradecode;
		if ($mode eq 'frag') { # Subroutine fragment
			$srcpre=$srcpre . "int foo(void) {\n";
			$srcpost="\n;\n  return 0;\n}\n" . $gradepost;
		}
	}
	elsif ( $lang eq "Fortran 77") { ############### Fortran 77
		$compiler="g77"; 
		$srcext="f";
		if ($mode eq 'frag') { # Subroutine fragment
		$srcpre='
      FUNCTION foo()
      INTEGER foo;
      ';
		$srcpost='
      END FUNCTION
'. $gradepost;
		}
		# FIXME: fortran name mangling is platform-dependent!
		push(@lflags,"-Dfoo=foo_");
		$main="lib/main.cpp"; # Must recompile main.cpp with new foo name
	}
	elsif ( $lang eq "Haskell") { # Fails with mkTextEncoding: invalid argument
		$compiler="ghc";
		$linker="ghc";
		$srcext="hs";
		$srcpre="";
		$srcpost="";
		$main=""; # Disable C-style main
	}
	elsif ( $lang eq "Prolog") { 
		$compiler="gplc";
		$linker="gplc";
		@cflags=();
		@lflags=();
		$srcext="pl";
		$srcpre="";
		$srcpost="";
		$srcflag="-c";
		$main=""; # Disable main
	}
	elsif ( $lang eq "Assembly") { ################# GNU Assembly
		$compiler="as"; 
		$disassembler="objdump -drC"; # Disassemble with GNU syntax...
		$srcext="S";
		$srcpre='
.section ".text" 
'. $gradecode .'
.globl foo
.type foo,@function
';
		if ($mode eq 'frag') { # Subroutine fragment
			$srcpre .="\nfoo:\n";
			$srcpost=$gradepost . "\nret";
		}
		$srcflag="";
		# @cflags=(); # Get rid of (C-specific) flags
	}
	elsif ( $lang eq "Assembly-NASM") { ################# NASM Assembly
		$compiler="nasm -f elf32 ";
		$srcext="S";
		$srcpre='
section .text
global foo
';
		if ($mode eq 'frag') { # Subroutine fragment
			$srcpre .="\nfoo:\n" . $gradecode;
			$srcpost=$gradepost . "\nret";
		} else {
			$srcpre .=$gradecode;
			$srcpost.=$gradepost;
		}
		$srcflag="";
	}
	elsif ( $lang eq "MPI") {
		$sr_host="powerwall0";
		$srcext='cpp';
		$compiler='mpiCC -msse3 ';
		$linker=$compiler;

		my $numprocs=2; # Sanity-check the processor count:
		if ($q->param('numprocs') =~ /^([0-9]+)$/) {
			if ($1>=1 && $1<=20) {
				$numprocs=$1;
			}
		}

		$saferun="netrun/safe_MPI.sh $numprocs ";
	}
	elsif ( $lang eq "CUDA") {
		$sr_host="powerwall0";
#		$sr_host="sandy";
		$srcext='cu';
		$compiler='/usr/local/cuda/bin/nvcc   -keep --opencc-options -LIST:source=on   ';
		$linker="$compiler -Xlinker -R/usr/local/cuda/lib ";
		$disassembler="cat code.ptx; echo ";
		# @cflags=();
		$srcflag="-c";
		$saferun="netrun/safe_CUDA.sh ";
	}
	elsif ( $lang eq "GPGPU") {
		$sr_host="powerwall0";
#		$sr_host="137.229.25.206";
		$srcext='cpp';
		$compiler='g++   ';
		$linker="$compiler ";
		push(@lflags,"/usr/lib/libglut_plain/libglut.a"); 
		push(@lflags,"/usr/lib/libGLEW.a");
		push(@lflags,"-lGLU -lGL");
		$compiler="$compiler -c";
		$saferun="netrun/safe_CUDA.sh ";
	}
	elsif ( $lang eq "OpenCL") {
		$sr_host="powerwall0";
#		$sr_host="sandy";
		$srcext='cpp';
		$compiler='g++   ';
		$linker="$compiler ";
		system("cp /usr/local/include/epgpu.* project/");
		push(@lflags,"-L/usr/local/cuda/include/"); 
		push(@cflags,"-I/usr/local/cuda/include/");
		push(@lflags,"/usr/lib/libglut_plain/libglut.a"); 
		push(@lflags,"/usr/lib/libGLEW.a");
		push(@lflags,"-lGL -lGLU -lOpenCL");
		$compiler="$compiler -c";
		$saferun="netrun/safe_CUDA.sh ";
	}
	elsif ( $lang eq "Python") {
		$netrun='netrun/scripting';
		$srcext='py';
		$saferun=$scriptrun . '/usr/bin/python '
	}
	elsif ( $lang eq "Python3") {
		$netrun='netrun/scripting';
		$srcext='py';
		$saferun=$scriptrun . '/usr/bin/python3 '
	}
	elsif ( $lang eq "Perl") {
		$netrun='netrun/scripting';
		$srcext='pl';
		$saferun=$scriptrun . '/usr/bin/perl '
	}
	elsif ( $lang eq "PHP") {
		$netrun='netrun/scripting';
		$srcext='php';
		$saferun=$scriptrun . '/usr/bin/php '
	}
	elsif ( $lang eq "JavaScript") {
		$netrun='netrun/scripting';
		$srcext='js';
		$saferun=$scriptrun . '/usr/bin/v8-shell  '
	}
	elsif ( $lang eq "Ruby") {
		$netrun='netrun/scripting';
		$srcext='rb';
		$saferun=$scriptrun . '/usr/bin/ruby  '
	}
	elsif ( $lang eq "Bash") {
		$netrun='netrun/scripting';
		$srcext='sh';
		$saferun=$scriptrun . '/bin/bash  '
	}
	elsif ( $lang eq "glfp") {
		$sr_host="powerwall6";
		if ($mode eq 'frag') { # Subroutine fragment
		$srcpre='!!ARBfp1.0
TEMP in,out;
MOV in,fragment.texcoord[0]; # Texture coordinate 0';
		$srcpost=$gradepost . '
MOV result.color,out;
END';
		}
		$srcext='glfp';
		$netrun='netrun/glfp';
	}
	elsif ( $lang eq "glsl") {
		$sr_host="powerwall6";
#		$sr_host="137.229.25.222";
		$srcpre='// GL Shading Language version 1.0 Fragment Shader
// Vertex/fragment shader interface
varying vec4 color; // Material diffuse color
varying vec3 position; // World-space coordinates of object
varying vec3 normal; // Surface normal (world space)
varying vec2 texcoords; // Texture coordinates
uniform sampler3D tex0; // input texture (noise)
uniform sampler2D tex1, tex3, tex4, tex5; // input textures (from files)
';
		if ($mode eq 'frag') { # Subroutine fragment
		$srcpre .= 'void main(void)
{';
		$srcpost=$gradepost . '
}
';
		}
		$srcext='glsl';
		$netrun='netrun/glsl';
	}
	elsif ( $lang eq "funk_emu") {
		$compiler="g++"; 
		$srcext="cpp";
		$srcpre='/* Here\'s the user\'s program, with bytes separated by commas... */
const int program[]={';

		# "Source code" is just a set of bytes separated by spaces.  Make them separated by commas.
		$code =~ s/[!#;].*//g;  # Remove comments
		$code =~ s/[\n\r]/ /g;  # Remove newlines
		$code =~ s/^[ 	]+//g;  # Remove leading whitespace
		$code =~ s/[ 	]+$//g;  # Remove trailing whitespace
		$code =~ s/[ 	]+/,/g;  # Whitespace to commas (makes an array of ints)

		$srcpost=my_cat("$config::run_dir/support/funk_emu_netrun.cpp");
	} 
	elsif ( $lang eq "spice") {
		$srcext='cir';
		$netrun='netrun/spice';
	}
	elsif ( $lang eq "vhdl") {
		$srcext='vhdl';
		$netrun='netrun/vhdl';
	}
	else {
		security_err("Invalid language '$lang'");
	}
	if ( $srcpost eq "") {
		$srcpost = $srcpost . $gradepost;
	}

	# Machine switch
	if ( $sr_host ne "" ) { # already set--nothing to do.
		
	} elsif ($netrun eq "netrun/scripting") { # The one scripting host
		$sr_host="sandy"; $sr_port=2984;
	}
	elsif ($mach eq "x86") {
	print "FYI-- This is a hyperthreaded 2.8GHz Intel Pentium 4 machine.<br>\n";
		$sr_host="olawlor";
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse3"); }
	} elsif ($mach eq "sandy64") {
	print "FYI-- This is a four-core Intel Sandy Bridge i5 2400.<br>\n";
		$sr_host="sandy";
		if ( $lang eq "Assembly-NASM") { $compiler="nasm -f elf64 ";}
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" || $lang eq "OpenMP" ) { push(@cflags,"-msse4.2 -mavx -msse2avx"); }
		if ($lang eq "OpenMP") {$compiler=$linker="g++ -fopenmp ";}
	} elsif ($mach eq "phenom64") {
	print "FYI-- This is a six-core AMD Phenom II.<br>\n";
		$sr_host="phenom";
		if ( $lang eq "Assembly-NASM") { $compiler="nasm -f elf64 ";}
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse4a -m3dnow"); }
		if ($lang eq "OpenMP") {$compiler=$linker="g++ -fopenmp ";}
	} elsif ( $mach eq "x86_atom") {
	print "FYI-- This is a 1.6Ghz Intel Atom 330 dual-core machine.<br>\n";
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse3"); }
		$sr_host="atomic";
	} elsif ( $mach eq "x86_2") {
	print "FYI-- This is a two CPU 1133MHz Intel Pentium III Xeon machine.<br>\n";
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse2"); }
		$sr_host="poweredge";
	} elsif ( $mach eq "x86_2core") {
	print "FYI-- This is a dual-core 1.8GHz Intel Core2 Duo machine.<br>\n";
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse3"); }
		$sr_host="powerwall8";
	} elsif ( $mach eq "x86_4core") {
	print "FYI-- This is a quad-core 2.4GHz Intel Core2 Q6600 machine.<br>\n";
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse3"); }
		$sr_host="viz1";
	} elsif ( $mach eq "x64") {
#	print "WARNING-- x64 machine is emulated with QEMU, and may be slow (10 seconds)<br>\n";
#		$sr_host="localhost";
#		$sr_port="9923";
		if ( $lang eq "Assembly-NASM") { $compiler="nasm -f elf64 ";}
		if ( $lang eq "Assembly" ) { $srcpost='ret'; }
		if ( $lang eq "C" || $lang eq "C++" ) { push(@cflags,"-msse3"); }
		$sr_host="viz1";
	} elsif ( $mach eq "ia64") {
	print "FYI-- This is a two CPU 800MHz Intel Itanium machine.<br>\n";
		$sr_host="itanium1";
	} elsif ( $mach eq "486") {
	print "FYI-- This is a 50MHz Intel 486 with 12MB RAM.  Please be patient!<br>\n";
		$sr_host="orlando";
		if ( $lang eq "C++") {print "Note that C compiles faster on this slow machine.<br>\n";}
		$disassembler="objdump -drC";   # -M freaks out this version
		# Compiling full set of headers takes *forever*, so strip down.
#		$srcpre='/* NetRun Minimal C/C++ Wrapper (Public Domain) */
#include <stdio.h>
#include "lib/inc.h"
#';
	} elsif ( $mach eq "Alpha") {
	print "FYI-- This is a 233Mhz DEC Alpha CPU with 32MB RAM<br>\n";
		$sr_host="dec1";
	} elsif ( $mach eq "SPARC") {
	print "FYI-- This is a 350MHz UltraSparc IIi CPU.<br>\n";
		$sr_host="ultra52";
	} elsif ( $mach eq "ARM") {
	print "FYI-- This is a 500MHz Samsung S3C6410 ARMv6 CPU.<br>\n";
		$sr_host="viz1";
		$sr_port=2984;
		$saferun="netrun/safe_arm.sh";
		$disassembler="objdump -drC";   # -M freaks out this version
		if ( $lang eq "Assembly") { ################# GNU Assembly
			$srcpre='
.syntax unified  @ no #constants
.section .text
'. $gradecode .'
.global foo
';
			if ($mode eq 'frag') { # Subroutine fragment
				$srcpre .="\nfoo:\n";
				$srcpost='bx lr'; 		
			}
		}

		
	} elsif ( $mach eq "win32") {
	print "WARNING-- Win32 machine is emulated with QEMU, and may be slow (half a minute!)<br>\n";
		@cflags=("/EHsc","/DWIN32=1");
		if (grep(/^Optimize$/, @ocompile)==1) {push(@cflags,"/O2");}
		if (grep(/^Time$/, @orun)==1) {push(@lflags,"/DTIME_FOO=1");}
		$srcflag="/c";
		$outflag="/o";
		# Run under WINE (slow, dangerous...)
		# $compiler=$linker="'/dos/Program Files/OrionDev/bin/cl.exe'";
		# $disassembler="/opt/cross/win32/bin/i386-mingw32msvc-objdump -drC";
		# Run on real or emulated windows box.
		$compiler=$linker='cl /nologo ';
		
		if ( $lang eq "C" ) {
		} elsif ( $lang eq "C++" ) {
		} else { err("Win32 $lang not supported yet--use inline assembly"); }
		$sr_host="olawlor";
		$sr_port="9943";
	} elsif ( $mach eq "MIPS") {
	print "FYI-- This is a 180MHz MIPS R5000 with 256MB RAM.<br>\n";
		$sr_host="sgi1";
		# Linking with no-abi causes error: "cannot mix PIC and non-PIC"
		if (grep(/^Run$/, @orun)==0 and grep(/^Grade$/, @orun)==0 and ($lang eq "C" or $lang eq "C++") ) {
		   print("Disassemble only: enabling less-cluttered compile mode \"-mno-abicalls\"<br>\n");
		   push(@cflags,"-mno-abicalls"); # Eliminate position-independent code clutter
		}
		if ( $lang eq "C++") {print "Note that namespaces aren't supported by this ancient g++ compiler.<br>\n";}
		if ( $lang eq "Assembly") {
			if (grep(/^Shared$/, @ocompile)==1) {
			    $compiler = "as -KPIC ";
			}
			$srcpre = "$srcpre\n.set noreorder\n";
			$srcpost = "jr \$31\nnop";
		}
		$disassembler="dis -Ch "   # IRIX disassembler
	} elsif ( $mach eq "PPC") { 
	print "FYI-- This is a 2GHz PowerPC G5 Mac.<br>\n";
		if ( $lang eq "Assembly" ) 
		{ # Special startup syntax for OS X assembler 
			$srcpost='blr'; 
			$srcpre='
.text
'. $gradecode .'
.globl _foo
';
			if ($mode eq 'frag') { # Subroutine fragment
				$srcpre .="\n_foo:\n";
				$srcpost="\nblr";
			}
		}
		$sr_host="ppc1";
	} elsif ( $mach eq "PPC_G4") { 
	print "FYI-- This is a 768MHz PowerPC G4 Mac running Linux.<br>\n";
		if ( $lang eq "Assembly" ) { $srcpost='blr'; }
		$sr_host="ppc2";
	} elsif ( $mach eq "PPC_EMU") {
	print "WARNING-- PowerPC machine is emulated with QEMU, and may be slow (10 seconds)<br>\n";
		if ( $lang eq "Assembly" ) { $srcpost='blr'; }
		$sr_host="olawlor";
		$sr_port="9933";
	}
	elsif ( $mach eq "PIC") {
	print "Patience: it takes about 10 seconds to upload a program to the PIC microcontroller...<br>\n";
		if ( $lang ne "C" ) { 
			print "Sorry, only C is supported";
			security_err("Invalid language for PIC controller");
		}
		# It's such a weird environment, almost nothing works:
		$netrun="netrun/pic";
		$disassembler='cat run/main.lst #';
		if (grep(/^Disassemble$/, @orun)==1) {$netrun="$netrun netrun/dis";}


		$srcpre="";
		$srcpost="";
		if ($lang eq "C") {
			$srcpre='#include "pic_setup.h"'
		}
		$sr_host="phenom";
		$sr_port="2883";
	}
	else {
		security_err("Invalid machine '$mach'");
	}
	
# Run it!
	# Write user's source code to a file.
	my $orig_name="$name";
	$name="code";
	my $src="project/$name.$srcext";
	open(SRC,">$src") or err("Cannot create source file $src");
	print SRC $srcpre,"\n\n",$code,"\n\n",$srcpost,"\n\n";
	close(SRC);
	
	# Write all their parameters to a .sav file
	my_mkdir("saved");
	open(SFILE,">$userdir/saved/$orig_name.sav") or err("Cannot create save file in $userdir");
	if ($orig_name =~ /^today\//) {
		$q->param('name',"Testing"); # Set name to 'Testing'
	}
	$q->save(*SFILE);
	close(SFILE);
	system("/bin/cp","$src","$userdir/saved/$orig_name.txt");
	
	# Write their input data
	my $input="";
	if ($q->param('input')) {
		$input="< input.txt";
		open(INPUT,">project/input.txt");
		my $inputdata=$q->param('input');
		$inputdata =~ s/\r//g; # get rid of annoying carriage-returns...
		print INPUT $inputdata;
		close(INPUT);
	}
	
	# Linkwith support:
	my $linkwith_targets="";
	my $linkwith_build="";
	my $linkwith_param=$q->param('linkwith');
	my $linkwith="";
	if ($linkwith_param and $linkwith_param =~ /^(-l[a-zA-Z0-9_.]*)$/ ) { # -lfoo
		push(@lflags,$1);
	} else { # Link with some other project
		$linkwith=untaint_name($linkwith_param);
	}
	my $linkwith_file="saved/$linkwith.sav";
	if (! $linkwith || $linkwith eq "Testing") { # Nothing to link (untaint does this...)
	}
	elsif ($linkwith eq $orig_name) {
		print "Skipping bogus self-link to '$linkwith'<br>";
	} elsif (! -r $linkwith_file) {
		print "Skipping missing link-with named '$linkwith'<br>";
	} else {# Actually linking with a real project
		print "Will link with project ".saved_file_link($linkwith)."<br>";
		$linkwith_targets='linkwith/code.obj';
		$linkwith_build='
linkwith/code.obj:
	@ echo -n "'.$linkwith.': " && cd linkwith && make -s netrun/obj
';
		# Save the old query, load and create the linkwith project:
		my $old_q=$q;
		load_file($linkwith_file);
		$q->param("linkwith",''); # Prevent infinite recursion: only one layer of links!
		$q->param("mach",$old_q->param("mach")); # Run on same machine
		chdir('project');
		create_project_directory(); # Recursively build project dir!
		system("mv project linkwith"); # Sub-project directory name
		chdir('..');
		$q=$old_q;
	}
	
	# Create a Makefile
	open(MAKEFILE,">project/Makefile") or err("Cannot create Makefile in $userdir");

	print MAKEFILE "#
# Makefile for small user program.
#    generated by NetRun, http://lawlor.cs.uaf.edu/netrun/
# NetRun by Orion Sky Lawlor, olawlor\@acm.org, 2005/09/23 (Public Domain)
#
NAME=$name
USER_CODE=\$\(NAME).$srcext
COMPILER=$compiler
CFLAGS=".join(" ",@cflags)."
LINKER=$linker
LFLAGS=".join(" ",@lflags)."
DISASSEMBLER=$disassembler
INPUT=$input
NETRUN=$netrun
MAIN=$main
HWNUM=$hwnum
STUDENT=$user
SAFERUN=$saferun
SRCFLAG=$srcflag
OUTFLAG=$outflag
LINKWITH=$linkwith_targets

all:

$linkwith_build

# All the targets are inside Makefile.post:
include Makefile.post
";
	close(MAKEFILE);
	
	# Return a hash reference to the run host, port, and source code
	my $proj={};
	$proj->{sr_host}=$sr_host;
	$proj->{sr_port}=$sr_port;
	$proj->{src}=$src;
	return $proj;
}

################ Utility Routines

# Usage: separate_text_binary(input_text_and_binary,output_just_binary)
sub separate_text_binary {
	my $INFILE=shift;
	my $outbin=shift;
	my $b=0;
	open(INFILE,"$INFILE") or err("Could not open input file $INFILE.");
	binmode(INFILE);
	open(BINFILE,">$outbin") or err("Could not create output file $outbin.");
	binmode(BINFILE);
	foreach my $line (<INFILE>) {
	   if ($b) { # binary mode
	       print BINFILE $line;
	   } else { # ASCII Mode
	       chomp($line);              # remove the newline from $line.
	       if ($line eq '<&@SNIP@&>') {
        	   $b=1;
	       } else { 
		   $line=~ s/\xe2\x80./\'/g; #<- Fix up silly gcc curly-quotes
        	   print "$line\n";
	       }
	   }
	}
	close(BINFILE);
}


# Debugging status:
sub my_stat {
	my $what=shift;
	#print "$what<br>\n";
}

# Start redirecting all output to this file
sub my_start_redir {
	my $outfile=shift;
	
	# (I/O redirection from: http://www.unix.org.ua/orelly/perl/cookbook/ch07_21.htm)
	# take copies of the file descriptors
	open(OLDOUT, ">&STDOUT");
	open(OLDERR, ">&STDERR");

	# redirect stdout and stderr
	open(STDOUT, ">$outfile")  or die "Can't redirect stdout: $!";
	open(STDERR, ">&STDOUT")  or die "Can't dup stdout: $!";
}

# Stop redirecting all output to the file
sub my_end_redir {
	# close the redirected filehandles
	close(STDOUT)                       or die "Can't close STDOUT: $!";
	close(STDERR)                       or die "Can't close STDERR: $!";

	# restore stdout and stderr
	open(STDERR, ">&OLDERR")            or die "Can't restore stderr: $!";
	open(STDOUT, ">&OLDOUT")            or die "Can't restore stdout: $!";

	# avoid leaks by closing the independent copies
	close(OLDOUT)                       or die "Can't close OLDOUT: $!";
	close(OLDERR)                       or die "Can't close OLDERR: $!";
}

# Run this command, telling the user about it.
#  Usage: <what to call command> <file to print on error> <command & args>
sub my_sysuser {
	my $what=shift;
	my $src=shift;
	my $cmd=join(" ",@_);
	print "Executing $what: '$cmd'";
	
	my $outfile="output";
	
	my_start_redir($outfile);

	# run the program
	my $res=system(@_);

	my_end_redir();
	
	if ($res != 0) {
		print $q->hr,$q->h2("$what Error:");
		my_prefile($outfile,'-bg','#FF8888');
		print "While running command '$cmd' with input file '$src':";
		my_prefile($src,'-line');
		exit(0);
	} else {
		( -z $outfile ) or my_prefile($outfile);
	}
	# my_stat "Back from: '$cmd'";
}

# Exec this command, redirecting our output to "output"
sub my_exec {
	my_start_redir("output");
	exec(@_);
}

# Cat this file into a preformatted & escaped HTML <pre> block.
sub my_prefile {
	my $src=shift;
	my $linePrint=0;
	my $lineNo=0;
	my $bgColor="#CCCCCC";
	while (@_) {
		my $arg=shift;
		if ($arg eq "-line") {$linePrint=1;}
		if ($arg eq "-bg") {$bgColor=shift;}
	}
	
	# Escape less-than and ampersand for HTML.
	my %escapes=();
	$escapes{'<'}="&lt;";
	$escapes{'>'}="&gt;";
	$escapes{'&'}="&amp;";
	$escapes{'"'}="&quot;";
	
	print"<TABLE><TR>";
	if ($linePrint) { # Add a narrow column of line numbers
		my $lineTot=`wc -l $src`;
		print "<TD><PRE>";
		for (my $i=0;$i<$lineTot;$i++) {print((1+$i)."\n");}
		print"</PRE></TD><TD>";
	}
	
	print '<TD BGCOLOR="'.$bgColor.'"><PRE>';
	my $line;
	open(F,"<$src") or err("Could not open file '$src'");
	foreach $line (<F>) {
		$line =~ s/([<&])/$escapes{$1}/eg;
		print $line;
	}
	print"</PRE>";
	
	print"</TD></TR></TABLE>";
}
