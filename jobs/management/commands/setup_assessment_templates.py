# Create this file as: jobs/management/commands/setup_assessment_templates.py
# Make sure the directories exist: jobs/management/ and jobs/management/commands/

from django.core.management.base import BaseCommand
from jobs.models import AssessmentQuestionTemplate


class Command(BaseCommand):
    help = 'Create default assessment question templates'

    def handle(self, *args, **options):
        # Default template for standard assessments
        default_template, created = AssessmentQuestionTemplate.objects.get_or_create(
            name="Standard Risk Assessment",
            defaults={
                'description': 'Standard risk assessment questions for all applications',
                'questions': [
                    {
                        'question': 'Has the candidate\'s employment history been verified?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Are there any gaps in the candidate\'s CV that need explanation?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Has the candidate\'s security clearance been independently verified?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Assessment notes',
                        'type': 'text',
                        'required': False
                    }
                ],
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created "Standard Risk Assessment" template')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Standard Risk Assessment template already exists')
            )

        # High-clearance template
        clearance_template, created = AssessmentQuestionTemplate.objects.get_or_create(
            name="High Clearance Assessment",
            defaults={
                'description': 'Additional assessment questions for high-clearance positions',
                'questions': [
                    {
                        'question': 'Has AGSVA been contacted to verify clearance status?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Are there any concerns about the candidate\'s background?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Has the candidate been briefed on security requirements?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Additional security notes',
                        'type': 'text',
                        'required': False
                    }
                ],
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created "High Clearance Assessment" template')
            )
        else:
            self.stdout.write(
                self.style.WARNING('High Clearance Assessment template already exists')
            )

        # Create a template for Defence-specific assessments
        defence_template, created = AssessmentQuestionTemplate.objects.get_or_create(
            name="Defence Contractor Assessment",
            defaults={
                'description': 'Specific assessment questions for Defence contractors',
                'questions': [
                    {
                        'question': 'Has the contractor worked with Defence before?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Are there any known conflicts with current Defence projects?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Has the contractor been briefed on Defence protocols?',
                        'type': 'boolean',
                        'required': True
                    },
                    {
                        'question': 'Previous Defence project performance',
                        'type': 'text',
                        'required': False
                    },
                    {
                        'question': 'Any additional Defence-specific considerations',
                        'type': 'text',
                        'required': False
                    }
                ],
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created "Defence Contractor Assessment" template')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Defence Contractor Assessment template already exists')
            )

        self.stdout.write(
            self.style.SUCCESS('Assessment template setup completed!')
        )