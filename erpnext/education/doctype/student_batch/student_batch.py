# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.education.utils import validate_duplicate_student
from frappe.utils import cint

class StudentBatch(Document):
	def validate(self):
		self.validate_mandatory_fields()
		self.validate_strength()
		# self.validate_students()
		# self.validate_and_set_child_table_fields()
		# validate_duplicate_student(self.students)

	def validate_mandatory_fields(self):
		if not self.academic_term:
			frappe.throw(_("Please select Academic Term"))
		if self.group_based_on == "Program & Stream" and not self.program_and_stream:
			frappe.throw(_("Please select Program And Course Field"))

	def validate_strength(self):
		if self.max_strength and len(self.students) > self.max_strength:
			frappe.throw(_("""Cannot enroll more than {0} students for this student group.""").format(self.max_strength))

	def validate_students(self):
		program_enrollment = get_program_enrollment(self.academic_year, self.academic_term, self.program, self.batch, self.student_category, self.course)
		students = [d.student for d in program_enrollment] if program_enrollment else []
		for d in self.students:
			if not frappe.db.get_value("Student", d.student, "enabled") and d.active and not self.disabled:
				frappe.throw(_("{0} - {1} is inactive student".format(d.group_roll_number, d.student_name)))

			if (self.group_based_on == "Batch") and cint(frappe.defaults.get_defaults().validate_batch)\
				and d.student not in students:
				frappe.throw(_("{0} - {1} is not enrolled in the Batch {2}".format(d.group_roll_number, d.student_name, self.batch)))

			if (self.group_based_on == "Course") and cint(frappe.defaults.get_defaults().validate_course)\
				and (d.student not in students):
				frappe.throw(_("{0} - {1} is not enrolled in the Course {2}".format(d.group_roll_number, d.student_name, self.course)))

	def validate_and_set_child_table_fields(self):
		roll_numbers = [d.group_roll_number for d in self.students if d.group_roll_number]
		max_roll_no = max(roll_numbers) if roll_numbers else 0
		roll_no_list = []
		for d in self.students:
			if not d.student_name:
				d.student_name = frappe.db.get_value("Student", d.student, "title")
			if not d.group_roll_number:
				max_roll_no += 1
				d.group_roll_number = max_roll_no
			if d.group_roll_number in roll_no_list:
				frappe.throw(_("Duplicate roll number for student {0}".format(d.student_name)))
			else:
				roll_no_list.append(d.group_roll_number)

@frappe.whitelist()
def get_students(academic_term, group_based_on, program_and_stream=None,campus=None):
	students_already_alloted_batch = frappe.get_all('Student Group Student',fields=['student','student_phone_number','student_email_id'])
	students_not_given_batch = []
	if group_based_on == 'Program & Stream' and program_and_stream:
		student_list = frappe.db.sql("""
		Select st.title as student,
		st.email_id as student_email_id,
		st.mobile_number as student_phone_number
		FROM 
		`tabEnroll Student` as st
		WHERE 
		st.enrolled_course = %(program_and_stream)s
		AND st.status = 'Active'
		AND st.current_academic_term = %(academic_term)s
		AND st.campus = %(campus)s
		""",{'program_and_stream':program_and_stream,'academic_term':academic_term,'campus':campus},as_dict=True)


	# if group_based_on == 'Program' and program :
	# 	student_list = frappe.db.sql("""

	# 	Select st.title as student,
	# 	st.email_id as student_email_id,
	# 	st.mobile_number as student_phone_number
		
	# 	FROM 
	# 	`tabEnroll Student` as st
	# 	JOIN `tabProgram Stream` as psb
	# 	on psb.program_stream_name = st.enrolled_course
	# 	JOIN `tabPograms` as p
	# 	ON p.name = psb.program
	# 	WHERE 
	# 	p.name = %(program)s
	# 	AND st.status = 'Active'
	# 	AND st.current_academic_term = %(academic_term)s
	# 	""",{'program':program,'academic_term':academic_term},as_dict=True)

	# if group_based_on == 'Stream' and stream :
	# 	student_list = frappe.db.sql("""
	# 	Select st.title as student,
	# 	st.email_id as student_email_id,
	# 	st.mobile_number as student_phone_number
		
	# 	FROM 
	# 	`tabEnroll Student` as st
	# 	JOIN `tabProgram Stream` as psb
	# 	on psb.program_stream_name = st.enrolled_course
	# 	JOIN `tabStream` as s
	# 	ON s.name = psb.stream
	# 	WHERE
	# 	s.name = %(stream)s
	# 	AND st.status = 'Active'
	# 	AND st.current_academic_term = %(academic_term)s
	# 	""",{'stream':stream,'academic_term':academic_term},as_dict=True)
	for st in student_list:
		if st not in students_already_alloted_batch:
			students_not_given_batch.append(st)
	if len(students_not_given_batch)==0:
		frappe.throw('No students or all students already alloted a batch')
	return students_not_given_batch

def get_program_enrollment(academic_year, academic_term=None, program=None, batch=None, student_category=None, course=None):
	
	condition1 = " "
	condition2 = " "
	if academic_term:
		condition1 += " and pe.academic_term = %(academic_term)s"
	if program:
		condition1 += " and pe.program = %(program)s"
	if batch:
		condition1 += " and pe.student_batch_name = %(batch)s"
	if student_category:
		condition1 += " and pe.student_category = %(student_category)s"
	if course:
		condition1 += " and pe.name = pec.parent and pec.course = %(course)s"
		condition2 = ", `tabProgram Enrollment Course` pec"

	return frappe.db.sql('''
		select 
			pe.student, pe.student_name 
		from 
			`tabProgram Enrollment` pe {condition2}
		where
			pe.academic_year = %(academic_year)s  {condition1}
		order by
			pe.student_name asc
		'''.format(condition1=condition1, condition2=condition2),
                ({"academic_year": academic_year, "academic_term":academic_term, "program": program, "batch": batch, "student_category": student_category, "course": course}), as_dict=1)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_students(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("group_based_on") != "Activity":
		enrolled_students = get_program_enrollment(filters.get('academic_year'), filters.get('academic_term'),
			filters.get('program'), filters.get('batch'), filters.get('student_category'))
		student_batch_student = frappe.db.sql_list('''select student from `tabStudent Batch Student` where parent=%s''',
			(filters.get('student_batch')))
		students = ([d.student for d in enrolled_students if d.student not in student_batch_student]
			if enrolled_students else [""]) or [""]
		return frappe.db.sql("""select name, title from tabStudent
			where name in ({0}) and (`{1}` LIKE %s or title LIKE %s)
			order by idx desc, name
			limit %s, %s""".format(", ".join(['%s']*len(students)), searchfield),
			tuple(students + ["%%%s%%" % txt, "%%%s%%" % txt, start, page_len]))
	else:
		return frappe.db.sql("""select name, title from tabStudent
			where `{0}` LIKE %s or title LIKE %s
			order by idx desc, name
			limit %s, %s""".format(searchfield),
			tuple(["%%%s%%" % txt, "%%%s%%" % txt, start, page_len]))

