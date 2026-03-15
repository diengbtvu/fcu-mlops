<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

class TrainingCompletedMail extends Mailable
{
    use Queueable, SerializesModels;

    public $trainingData;
    public $result;

    /**
     * Create a new message instance.
     */
    public function __construct($trainingData, $result)
    {
        $this->trainingData = $trainingData;
        $this->result = $result;
    }

    /**
     * Get the message envelope.
     */
    public function envelope(): Envelope
    {
        $status = $this->result['success'] ? 'Completed Successfully' : 'Failed';
        
        return new Envelope(
            subject: "Model Training {$status} - {$this->trainingData['model_type']}",
        );
    }

    /**
     * Get the message content definition.
     */
    public function content(): Content
    {
        return new Content(
            view: 'emails.training-completed',
        );
    }

    /**
     * Get the attachments for the message.
     *
     * @return array<int, \Illuminate\Mail\Mailables\Attachment>
     */
    public function attachments(): array
    {
        return [];
    }
}
