# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from .addon_updater import Updater as updater
from bpy.app.handlers import persistent
import os

# Must declare this before classes are loaded
# otherwise the bl_idnames will not match and have errors.
# Must be all lowercase and no spaces
updater.addon = "kaleidoscope"


# -----------------------------------------------------------------------------
# Updater operators
# -----------------------------------------------------------------------------


# simple popup for prompting checking for update & allow to install if available
class addon_updater_install_popup(bpy.types.Operator):
	"""Check and install update if available"""
	bl_label = "Update {x} addon".format(x=updater.addon.title())
	bl_idname = updater.addon+".updater_install_popup"
	bl_description = "Popup menu to check and display current updates available"

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		if updater.update_ready == True:
			layout.label("Update ready! Press OK to install v"\
						+str(updater.update_version))
			layout.label("or click outside window to defer")
			# could offer to remove popups here, but window will not redraw
			# so may be confusing to the user/look like a bug
			# row = layout.row()
			# row.label("Prevent future popups:")
			# row.operator(addon_updater_ignore.bl_idname,text="Ignore update")
		elif updater.update_ready == False:
			layout.label("No updates available")
			layout.label("Press okay to dismiss dialog")
			# add option to force install
		else:
			# case: updater.update_ready = None
			# we have not yet checked for the update
			layout.label("Check for update now?")

		# potentially in future, could have UI for 'check to select old version'
		# to revert back to.

	def execute(self,context):

		if updater.update_ready == True:
			res = updater.run_update(force=False, callback=post_update_callback)
			# should return 0, if not something happened
			if updater.verbose:
				if res==0: print("Updater returned successful")
				else: print("Updater returned "+str(res)+", error occured")

		elif updater.update_ready == None:
			(update_ready, version, link) = updater.check_for_update(now=True)

			# re-launch this dialog
			atr = addon_updater_install_popup.bl_idname.split(".")
			getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')
			#bpy.ops.retopoflow.updater_install_popup('INVOKE_DEFAULT')

		else:
			if updater.verbose:print("Doing nothing, not ready for update")
		return {'FINISHED'}


# User preference check-now operator
class addon_updater_check_now(bpy.types.Operator):
	bl_label = "Check now for "+updater.addon.title()+" update"
	bl_idname = updater.addon+".updater_check_now"
	bl_description = "Check now for an update to the {x} addon".format(
														x=updater.addon.title())

	def execute(self,context):

		if updater.async_checking == True and updater.error == None:
			# Check already happened
			# Used here to just avoid constant applying settings below
			# Ignoring if erro, to prevent being stuck on the error screen
			return {'CANCELLED'}
			return

		# apply the UI settings

		# input is an optional callback function
		# this function should take a bool input, if true: update ready
		# if false, no update ready
		updater.check_for_update_now()

		return {'FINISHED'}

class addon_updater_update_now(bpy.types.Operator):
	bl_label = "Update "+updater.addon.title()+" addon now"
	bl_idname = updater.addon+".updater_update_now"
	bl_description = "Update to the latest verison of the {x} addon".format(
														x=updater.addon.title())


	def execute(self,context):

		if updater.update_ready == True:
			# if it fails, offer to open the website instead
			try:
				res = updater.run_update(
						force=False,
						callback=post_update_callback)

				# should return 0, if not something happened
				if updater.verbose:
					if res==0: print("Updater returned successful")
					else: print("Updater returned "+str(res)+", error occured")
			except:
				atr = addon_updater_install_manually.bl_idname.split(".")
				getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')
		elif updater.update_ready == None:
			(update_ready, version, link) = updater.check_for_update(now=True)
			# re-launch this dialog
			atr = addon_updater_install_popup.bl_idname.split(".")
			getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')

		elif updater.update_ready == False:
			self.report({'INFO'}, "Nothing to update")
		else:
			self.report({'ERROR'}, "Encountered problem while trying to update")

		return {'FINISHED'}


class addon_updater_update_target(bpy.types.Operator):
	bl_label = updater.addon.title()+" addon version target"
	bl_idname = updater.addon+".updater_update_target"
	bl_description = "Install a targeted version of the {x} addon".format(
														x=updater.addon.title())

	def target_version(self, context):
		ret = []
		i=0
		for tag in updater.tags:
			ret.append( (tag,tag,"Select to install version "+tag) )
			i+=1
		return ret

	target = bpy.props.EnumProperty(
		name="Target version",
		description="Select the version to install",
		items=target_version
		)

	@classmethod
	def poll(cls, context):
		return updater.update_ready != None and len(updater.tags)>0

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		col = layout.column(align=True)
		col.separator()
		row = col.row(align=True)
		row.label("Select install version")
		row.prop(self, "target", text="")
		col.separator()

	def execute(self,context):

		res = updater.run_update(
				force=False,
				revert_tag=self.target,
				callback=post_update_callback)

		# should return 0, if not something happened
		if updater.verbose:
			if res==0: print("Updater returned successful")
			else: print("Updater returned "+str(res)+", error occurred")
		# try:
		#   updater.run_update(force=False,revert_tag=self.target)
		# except:
		#   self.report({'ERROR'}, "Problem installing target version")

		return {'FINISHED'}


class addon_updater_install_manually(bpy.types.Operator):
	"""As a fallback, direct the user to download the addon manually"""
	bl_label = "Install update manually"
	bl_idname = updater.addon+".updater_install_manually"
	bl_description = "Proceed to manually install update"

	def invoke(self, context, event):
		return context.window_manager.invoke_popup(self)

	def draw(self, context):
		layout = self.layout
		# use a "failed flag"? it show this label if the case failed.
		if False:
			layout.label("There was an issue trying to auto-install")
		else:
			layout.label("Install the addon manually")
			layout.label("Press the download button below and install")
			layout.label("the zip file like a normal addon.")

		# if check hasn't happened, ie accidentally called this menu
		# allow to check here

		row = layout.row()

		if updater.update_link != None:
			row.operator("wm.url_open",text="Direct download").url=\
					updater.update_link
		else:
			row.operator("wm.url_open",text="(failed to retreive)")
			row.enabled = False

			if updater.website != None:
				row = layout.row()
				row.label("Grab update from account")

				row.operator("wm.url_open",text="Open website").url=\
						updater.website
			else:
				row = layout.row()

				row.label("See source website to download the update")

	def execute(self,context):

		return {'FINISHED'}


class addon_updater_updated_successful(bpy.types.Operator):
	"""Addon in place, popup telling user it completed"""
	bl_label = "Success"
	bl_idname = updater.addon+".updater_update_successful"
	bl_description = "Update installation was successful"
	bl_options = {'REGISTER', 'UNDO'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_popup(self, event)

	def draw(self, context):
		layout = self.layout
		# use a "failed flag"? it show this label if the case failed.
		saved = updater.json
		if updater.auto_reload_post_update == False:
			# tell user to restart blender
			if "just_restored" in saved and saved["just_restored"] == True:
				layout.label("Addon restored")
				layout.label("Restart blender to reload.")
				updater.json_reset_restore()
			else:
				layout.label("Addon successfully installed")
				layout.label("Restart blender to reload.")

		else:
			# reload addon, but still recommend they restart blender
			if "just_restored" in saved and saved["just_restored"] == True:
				layout.label("Addon restored")
				layout.label("Consider restarting blender to fully reload.")
				updater.json_reset_restore()
			else:
				layout.label("Addon successfully installed.")
				layout.label("Consider restarting blender to fully reload.")

	def execut(self, context):
		return {'FINISHED'}


class addon_updater_restore_backup(bpy.types.Operator):
	"""Restore addon from backup"""
	bl_label = "Restore backup"
	bl_idname = updater.addon+".updater_restore_backup"
	bl_description = "Restore addon from backup"

	@classmethod
	def poll(cls, context):
		try:
			return os.path.isdir(os.path.join(updater.stage_path,"backup"))
		except:
			return False

	def execute(self, context):
		updater.restore_backup()
		return {'FINISHED'}


class addon_updater_ignore(bpy.types.Operator):
	"""Prevent future update notice popups"""
	bl_label = "Ignore update"
	bl_idname = updater.addon+".updater_ignore"
	bl_description = "Ignore update to prevent future popups"

	@classmethod
	def poll(cls, context):
		if updater.update_ready == True:
			return True
		else:
			return False

	def execute(self, context):
		updater.ignore_update()
		self.report({"INFO"},"Open addon preferences for updater options")
		return {'FINISHED'}


class addon_updater_end_background(bpy.types.Operator):
	"""Stop checking for update in the background"""
	bl_label = "End background check"
	bl_idname = updater.addon+".end_background_check"
	bl_description = "Stop checking for update in the background"

	# @classmethod
	# def poll(cls, context):
	#   if updater.async_checking == True:
	#       return True
	#   else:
	#       return False

	def execute(self, context):
		updater.stop_async_check_update()
		return {'FINISHED'}


# -----------------------------------------------------------------------------
# Handler related, to create popups
# -----------------------------------------------------------------------------


# global vars used to prevent duplicate popup handlers
ran_autocheck_install_popup = False
ran_update_sucess_popup = False

# global var for preventing successive calls
ran_background_check = False

@persistent
def updater_run_success_popup_handler(scene):
	global ran_update_sucess_popup
	ran_update_sucess_popup = True
	try:
		bpy.app.handlers.scene_update_post.remove(
				updater_run_success_popup_handler)
	except:
		pass

	atr = addon_updater_updated_successful.bl_idname.split(".")
	getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')


@persistent
def updater_run_install_popup_handler(scene):
	global ran_autocheck_install_popup
	ran_autocheck_install_popup = True
	try:
		bpy.app.handlers.scene_update_post.remove(
				updater_run_install_popup_handler)
	except:
		pass

	if "ignore" in updater.json and updater.json["ignore"] == True:
		return # don't do popup if ignore pressed
	atr = addon_updater_install_popup.bl_idname.split(".")
	getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')


# passed into the updater, background thread updater
def background_update_callback(update_ready):
	global ran_autocheck_install_popup

	if update_ready != True:
		return

	if updater_run_install_popup_handler not in \
				bpy.app.handlers.scene_update_post and \
				ran_autocheck_install_popup==False:
		bpy.app.handlers.scene_update_post.append(
				updater_run_install_popup_handler)

		ran_autocheck_install_popup = True


# a callback for once the updater has completed
# Only makes sense to use this if "auto_reload_post_update" == False,
# ie don't auto-restart the addon
def post_update_callback():
	# this is the same code as in conditional at the end of the register function
	# ie if "auto_reload_post_update" == True, comment out this code
	if updater.verbose: print("Running post update callback")
	#bpy.app.handlers.scene_update_post.append(updater_run_success_popup_handler)

	atr = addon_updater_updated_successful.bl_idname.split(".")
	getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')
	global ran_update_sucess_popup
	ran_update_sucess_popup = True
	return


# function for asynchronous background check, which *could* be called on register
def check_for_update_background(context):

	global ran_background_check
	if ran_background_check == True:
		# Global var ensures check only happens once
		return
	elif updater.update_ready != None or updater.async_checking == True:
		# Check already happened
		# Used here to just avoid constant applying settings below
		return

	# apply the UI settings
	settings = context.user_preferences.addons[__package__].preferences
	updater.set_check_interval(enable=settings.auto_check_update,
				months=settings.updater_intrval_months,
				days=settings.updater_intrval_days,
				hours=settings.updater_intrval_hours,
				minutes=settings.updater_intrval_minutes
				) # optional, if auto_check_update

	# input is an optional callback function
	# this function should take a bool input, if true: update ready
	# if false, no update ready
	if updater.verbose: print("Running background check for update")
	updater.check_for_update_async(background_update_callback)
	ran_background_check = True


# can be placed in front of other operators to launch when pressed
def check_for_update_nonthreaded(self, context):

	# only check if it's ready, ie after the time interval specified
	# should be the async wrapper call here

	settings = context.user_preferences.addons[__package__].preferences
	updater.set_check_interval(enable=settings.auto_check_update,
				months=settings.updater_intrval_months,
				days=settings.updater_intrval_days,
				hours=settings.updater_intrval_hours,
				minutes=settings.updater_intrval_minutes
				) # optional, if auto_check_update

	(update_ready, version, link) = updater.check_for_update(now=False)
	if update_ready == True:
		atr = addon_updater_install_popup.bl_idname.split(".")
		getattr(getattr(bpy.ops, atr[0]),atr[1])('INVOKE_DEFAULT')
	else:
		if updater.verbose: print("No update ready")
		self.report({'INFO'}, "No update ready")

# for use in register only, to show popup after re-enabling the addon
# must be enabled by developer
def showReloadPopup():
	saved_state = updater.json
	global ran_update_sucess_popup

	a = saved_state != None
	b = "just_updated" in saved_state
	c = saved_state["just_updated"]

	if a and b and c:
		updater.json_reset_postupdate() # so this only runs once

		# no handlers in this case
		if updater.auto_reload_post_update == False: return

		if updater_run_success_popup_handler not in \
					bpy.app.handlers.scene_update_post \
					and ran_update_sucess_popup==False:
			bpy.app.handlers.scene_update_post.append(
					updater_run_success_popup_handler)
			ran_update_sucess_popup = True


# -----------------------------------------------------------------------------
# Example includable UI integrations
# -----------------------------------------------------------------------------


# UI to place e.g. at the end of a UI panel where to notify update available
def update_notice_box_ui(self, context):

	saved_state = updater.json
	if updater.auto_reload_post_update == False:
		if "just_updated" in saved_state and saved_state["just_updated"] == True:
			layout = self.layout
			box = layout.box()
			box.label("Restart blender", icon="ERROR")
			box.label("to complete update")
			return

	# if user pressed ignore, don't draw the box
	if "ignore" in updater.json and updater.json["ignore"] == True:
		return

	if updater.update_ready != True: return

	settings = context.user_preferences.addons[__package__].preferences
	layout = self.layout
	box = layout.box()
	col = box.column(align=True)
	col.label("Update ready!",icon="ERROR")
	col.operator("wm.url_open", text="Open website").url = updater.website
	#col.operator("wm.url_open",text="Direct download").url=updater.update_link
	col.operator(addon_updater_install_manually.bl_idname, "Install manually")
	if updater.manual_only==False:
		col.operator(addon_updater_update_now.bl_idname,
						"Update now", icon="LOOP_FORWARDS")
	col.operator(addon_updater_ignore.bl_idname,icon="X")



# create a function that can be run inside user preferences panel for prefs UI
# place inside UI draw using: addon_updater_ops.updaterSettingsUI(self, context)
# or by: addon_updater_ops.updaterSettingsUI(context)
def update_settings_ui(self, context):
	settings = context.user_preferences.addons[__package__].preferences

	layout = self.layout
	box = layout.box()

	# auto-update settings
	box.label("Updater Settings")
	row = box.row()

	# special case to tell user to restart blender, if set that way
	if updater.auto_reload_post_update == False:
		saved_state = updater.json
		if "just_updated" in saved_state and saved_state["just_updated"] == True:
			row.label("Restart blender to complete update", icon="INFO")
			return

	# checking / managing updates
	row = box.row()
	split_c = row.split(percentage=0.7)
	col = split_c.column()
	separators = 10
	button_scale = 1.5
	movemosue = False
	if updater.error != None:
		subcol = col.row(align=True)
		subcol.scale_y = 1
		split = subcol.split(align=True)
		split.enabled = False
		split.scale_y = button_scale
		row_i = split.row(align=True)
		row_i.scale_y=button_scale
		for i in range(1, separators):
			row_i.separator()
		row_i.operator(addon_updater_check_now.bl_idname,
						updater.error)
		row_i.operator(addon_updater_check_now.bl_idname,
						text = "", icon="FILE_REFRESH")
		for i in range(1, separators):
			row_i.separator()

	elif updater.update_ready == None and updater.async_checking == False:
		row_i = col.row(align=True)
		row_i.scale_y = button_scale
		for i in range(1, separators):
			row_i.separator()
		row_i.operator(addon_updater_check_now.bl_idname, icon='WORLD')
		for i in range(1, separators):
			row_i.separator()
	elif updater.update_ready == None: # async is running
		subcol = col.row(align=True)
		subcol.scale_y = 1
		split = subcol.split(align=True)
		split.enabled = False
		split.scale_y = button_scale
		row_i = split.row(align=True)
		row_i.scale_y = button_scale
		for i in range(1, separators):
			row_i.separator()
		row_i.operator(addon_updater_check_now.bl_idname,
						"Checking...", icon='URL')
		row_i.operator(addon_updater_end_background.bl_idname,
						text = "", icon="X")
		for i in range(1, separators):
			row_i.separator()

	elif updater.update_ready==True and updater.manual_only==False:
		subcol = col.row(align=True)
		subcol.scale_y = 1
		split = subcol.split(align=True)
		split.scale_y = button_scale
		row_i = split.row(align=True)
		row_i.scale_y = button_scale
		for i in range(1, separators):
			row_i.separator()
		row_i.operator(addon_updater_update_now.bl_idname,
					"Update now to "+str(updater.update_version), icon='SAVE_AS')

		row_i.operator(addon_updater_check_now.bl_idname,
						text = "", icon="FILE_REFRESH")
		for i in range(1, separators):
			row_i.separator()

	elif updater.update_ready==True and updater.manual_only==True:
		col.scale_y = button_scale
		col.operator("wm.url_open",
				"Download "+str(updater.update_version)).url=updater.website
	else: # ie that updater.update_ready == False
		subcol = col.row(align=True)
		subcol.scale_y = 1
		split = subcol.split(align=True)
		split.enabled = False
		split.scale_y = button_scale
		row_i = split.row(align=True)
		row_i.scale_y = button_scale
		for i in range(1, separators):
			row_i.separator()
		row_i.operator(addon_updater_check_now.bl_idname,
						"Addon is up to date")
		row_i.operator(addon_updater_check_now.bl_idname,
						text = "", icon="FILE_REFRESH")
		for i in range(1, separators):
			row_i.separator()

	if updater.manual_only == False:
		col = split_c.column(align=True)
		col = col.row(align=True)
		col.scale_y = button_scale
		if updater.include_master == True:
			col.operator(addon_updater_update_target.bl_idname,
					"Install old verison", icon='PREFERENCES')
		else:
			col.operator(addon_updater_update_target.bl_idname,
					"Reinstall / install old verison", icon='PREFERENCES')
		lastdate = "none found"
		backuppath = os.path.join(updater.stage_path,"backup")
		if "backup_date" in updater.json and os.path.isdir(backuppath):
			if updater.json["backup_date"] == "":
				lastdate = "Date not found"
			else:
				lastdate = updater.json["backup_date"]
		col.operator(addon_updater_restore_backup.bl_idname, text="", icon='LOAD_FACTORY')

	row = box.row()
	lastcheck = updater.json["last_check"]
	if updater.error != None and updater.error_msg != None:
		row.label(updater.error_msg)
	elif movemosue == True:
		row.label("Move mouse if button doesn't update")
	elif lastcheck != "" and lastcheck != None:
		lastcheck = lastcheck[0: lastcheck.index(".") ]
		row.label("Last update check: " + lastcheck)
	else:
		row.label("Last update check: None")


# a global function for tag skipping
# a way to filter which tags are displayed,
# e.g. to limit downgrading too far
# input is a tag text, e.g. "v1.2.3"
# output is True for skipping this tag number,
# False if the tag is allowed (default for all)
def skip_tag_function(tag):

	# ---- write any custom code here, return true to disallow version ---- #
	#
	# # Filter out e.g. if 'beta' is in name of release
	# if 'beta' in tag.lower():
	#   return True
	# ---- write any custom code above, return true to disallow version --- #

	if tag["name"].lower() == 'master' and updater.include_master == True:
		return False

	# function converting string to tuple, ignoring e.g. leading 'v'
	tupled = updater.version_tuple_from_text(tag["name"])
	if type(tupled) != type( (1,2,3) ): return True # master

	# select the min tag version - change tuple accordingly
	if updater.version_min_update != None:
		if tupled < updater.version_min_update:
			return True # skip if current version below this

	# select the max tag version
	if updater.version_max_update != None:
		if tupled >= updater.version_max_update:
			return True # skip if current version at or above this

	# in all other cases, allow showing the tag for updating/reverting
	return False


# -----------------------------------------------------------------------------
# Register, should be run in the register module itself
# -----------------------------------------------------------------------------


# registering the operators in this module
def register(bl_info):

	# See output to verify this register function is working properly
	# print("Running updater reg")

	# choose your own username
	updater.user = "blenderskool"

	# choose your own repository, must match github name
	updater.repo = "kaleidoscope"

	#updater.addon = # define at top of module, must be done first

	# Website for manual addon download, optional
	updater.website = "https://github.com/blenderskool/kaleidoscope/"

	# used to check/compare versions
	updater.current_version = bl_info["version"]

	# to hard-set udpate frequency, use this here - however, this demo
	# has this set via UI properties. Optional
	# updater.set_check_interval(
	# 		enable=False,months=0,days=0,hours=0,minutes=2)

	# optional, consider turning off for production or allow as an option
	# This will print out additional debugging info to the console
	updater.verbose = True # make False for production default

	# optional, customize where the addon updater processing subfolder is,
	# needs to be within the same folder as the addon itself
	# updater.updater_path = # set path of updater folder, by default:
	#			/addons/{__package__}/{__package__}_updater

	# auto create a backup of the addon when installing other versions
	updater.backup_current = True # True by default

	# allow 'master' as an option to update to, skipping any releases.
	# releases are still accessible from re-install menu
	updater.include_master = True

	# only allow manual install, thus prompting the user to open
	# the webpage to download but not auto-installing. Useful if
	# only wanting to get notification of updates
	# updater.manual_only = True

	# used for development only, "pretend" to install an update to test
	# reloading conditions
	updater.fake_install = False # Set to true to test callback/reloading

	# Override with a custom function on what tags
	# to skip showing for udpater; see code for function above.
	# Set the min and max versions allowed to install.
	# Optional, default None
	updater.version_min_update = (0,0,0) # min install (>=) will install this and higher
	# updater.version_min_update = None  # if not wanting to define a min
	updater.version_max_update = (9,9,9) # max install (<) will install strictly anything lower
	# updater.version_max_update = None  # if not wanting to define a max
	updater.skip_tag = skip_tag_function # min and max used in this function

	# The register line items for all operators/panels
	# If using bpy.utils.register_module(__name__) to register elsewhere
	# in the addon, delete these lines (also from unregister)
	# special situation: we just updated the addon, show a popup
	# to tell the user it worked
	# should be enclosed in try/catch in case other issues arise
	showReloadPopup()


def unregister():

	# clear global vars since they may persist if not restarting blender
	global ran_autocheck_install_popup
	ran_autocheck_install_popup = False

	global ran_update_sucess_popup
	ran_update_sucess_popup = False

	global ran_background_check
	ran_background_check = False