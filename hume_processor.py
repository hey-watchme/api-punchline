"""
Hume Emotional Data Processor for PUNCHLINE API

This module provides utilities to compress and extract meaningful emotional
insights from Hume AI analysis data (50,000+ tokens → 100 tokens).
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class HumeProcessor:
    """Process and compress Hume emotional analysis data"""

    # Emotion thresholds for significance
    STRONG_EMOTION_THRESHOLD = 0.4
    MODERATE_EMOTION_THRESHOLD = 0.3
    TRANSITION_THRESHOLD = 0.2

    # Categories of emotions for grouping
    POSITIVE_EMOTIONS = ['Joy', 'Excitement', 'Amusement', 'Love', 'Satisfaction', 'Pride']
    NEGATIVE_EMOTIONS = ['Sadness', 'Anger', 'Fear', 'Anxiety', 'Disappointment', 'Shame']
    COGNITIVE_EMOTIONS = ['Contemplation', 'Interest', 'Realization', 'Concentration', 'Confusion']

    @staticmethod
    def extract_emotional_peaks(
        hume_data: Dict[str, Any],
        top_n: int = 5,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Extract the most significant emotional peaks from Hume data.

        Args:
            hume_data: Raw Hume analysis data
            top_n: Number of top peaks to extract
            threshold: Minimum emotion score to consider

        Returns:
            List of emotional peak moments with time and intensity
        """
        peaks = []

        # Process speech_prosody segments (most detailed)
        prosody = hume_data.get('speech_prosody', {})
        segments = prosody.get('segments', [])

        for segment in segments:
            dominant = segment.get('dominant_emotion', {})
            if dominant.get('score', 0) >= threshold:
                peaks.append({
                    'time': segment.get('time', {}).get('begin', 0),
                    'emotion': dominant.get('name', 'Unknown'),
                    'score': round(dominant.get('score', 0), 2),
                    'text_snippet': segment.get('text', '')[:30] + '...'
                })

        # Add vocal bursts if significant
        vocal_bursts = hume_data.get('vocal_burst', {})
        for burst in vocal_bursts.get('segments', []):
            dominant = burst.get('dominant_emotion', {})
            if dominant.get('score', 0) >= threshold:
                peaks.append({
                    'time': burst.get('time', {}).get('begin', 0),
                    'emotion': f"VocalBurst:{dominant.get('name', 'Unknown')}",
                    'score': round(dominant.get('score', 0), 2),
                    'text_snippet': '[Non-verbal expression]'
                })

        # Sort by score and return top N
        peaks.sort(key=lambda x: x['score'], reverse=True)
        return peaks[:top_n]

    @staticmethod
    def detect_emotional_transitions(
        hume_data: Dict[str, Any],
        change_threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Detect significant emotional transitions in the conversation.

        Args:
            hume_data: Raw Hume analysis data
            change_threshold: Minimum change to consider significant

        Returns:
            List of emotional transition points
        """
        transitions = []
        prosody = hume_data.get('speech_prosody', {})
        segments = prosody.get('segments', [])

        for i in range(1, len(segments)):
            prev_emotion = segments[i-1].get('dominant_emotion', {})
            curr_emotion = segments[i].get('dominant_emotion', {})

            # Check if emotion changed significantly
            if prev_emotion.get('name') != curr_emotion.get('name'):
                if curr_emotion.get('score', 0) >= change_threshold:
                    transitions.append({
                        'time': segments[i].get('time', {}).get('begin', 0),
                        'from_emotion': prev_emotion.get('name', 'Unknown'),
                        'to_emotion': curr_emotion.get('name', 'Unknown'),
                        'intensity': round(curr_emotion.get('score', 0), 2)
                    })

        return transitions

    @staticmethod
    def create_emotional_summary(
        hume_data: Dict[str, Any],
        strategy: str = 'peaks',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a compressed emotional summary suitable for LLM prompts.

        Args:
            hume_data: Raw Hume analysis data
            strategy: 'peaks', 'transitions', or 'full_summary'
            **kwargs: Additional parameters for specific strategies

        Returns:
            Compressed emotional context (< 100 tokens)
        """
        processor = HumeProcessor()
        summary = {}

        # Get overall mood from language analysis
        language = hume_data.get('language', {})
        if language.get('segments'):
            dominant_emotion = language['segments'][0].get('dominant_emotion', {})
            summary['overall_mood'] = dominant_emotion.get('name', 'Unknown')
            summary['mood_confidence'] = round(dominant_emotion.get('score', 0), 2)

        if strategy == 'peaks':
            # Extract emotional peaks
            threshold = kwargs.get('threshold', 0.3)
            top_n = kwargs.get('top_n', 5)
            peaks = processor.extract_emotional_peaks(hume_data, top_n, threshold)
            summary['emotional_peaks'] = peaks

        elif strategy == 'transitions':
            # Detect emotional transitions
            change_threshold = kwargs.get('change_threshold', 0.2)
            transitions = processor.detect_emotional_transitions(hume_data, change_threshold)
            summary['emotional_transitions'] = transitions[:5]  # Limit to 5

        elif strategy == 'full_summary':
            # Combined approach
            peaks = processor.extract_emotional_peaks(hume_data, 3, 0.35)
            transitions = processor.detect_emotional_transitions(hume_data, 0.25)

            summary['key_moments'] = []
            for peak in peaks[:2]:
                summary['key_moments'].append({
                    'time': f"{peak['time']:.1f}s",
                    'event': f"{peak['emotion']} ({peak['score']*100:.0f}%)"
                })

            # Create emotional arc
            if len(transitions) > 0:
                arc_parts = []
                if transitions[0]['from_emotion'] not in arc_parts:
                    arc_parts.append(transitions[0]['from_emotion'])
                for t in transitions[:3]:
                    if t['to_emotion'] not in arc_parts:
                        arc_parts.append(t['to_emotion'])
                summary['emotional_arc'] = ' → '.join(arc_parts)

        return summary

    @staticmethod
    def format_for_prompt(emotional_summary: Dict[str, Any]) -> str:
        """
        Format emotional summary for inclusion in LLM prompt.

        Args:
            emotional_summary: Compressed emotional data

        Returns:
            Formatted string for prompt inclusion (< 100 tokens)
        """
        lines = []

        if 'overall_mood' in emotional_summary:
            lines.append(f"Overall mood: {emotional_summary['overall_mood']}")

        if 'emotional_peaks' in emotional_summary:
            peaks = emotional_summary['emotional_peaks']
            if peaks:
                peak_strs = [f"[{p['time']:.0f}s: {p['emotion']} {p['score']*100:.0f}%]"
                            for p in peaks[:3]]
                lines.append(f"Peak moments: {', '.join(peak_strs)}")

        if 'emotional_arc' in emotional_summary:
            lines.append(f"Emotional journey: {emotional_summary['emotional_arc']}")

        if 'key_moments' in emotional_summary:
            moments = [f"{m['event']} at {m['time']}"
                      for m in emotional_summary['key_moments'][:2]]
            lines.append(f"Key moments: {', '.join(moments)}")

        return '\n'.join(lines)

    @staticmethod
    def identify_punchline_candidates(
        hume_data: Dict[str, Any],
        time_window: float = 2.0
    ) -> List[Tuple[float, float, str]]:
        """
        Identify time ranges likely to contain punchlines based on emotions.

        Args:
            hume_data: Raw Hume analysis data
            time_window: Time window around emotional peaks (seconds)

        Returns:
            List of (start_time, end_time, reason) tuples
        """
        candidates = []
        processor = HumeProcessor()

        # Get emotional peaks
        peaks = processor.extract_emotional_peaks(hume_data, top_n=10, threshold=0.25)

        for peak in peaks:
            start = max(0, peak['time'] - time_window)
            end = peak['time'] + time_window

            # Determine punchline type based on emotion
            if peak['emotion'] in ['Amusement', 'Joy', 'Excitement']:
                reason = 'High humor/joy moment'
            elif peak['emotion'] in ['Sadness', 'Empathic Pain']:
                reason = 'Emotional/touching moment'
            elif peak['emotion'] in ['Surprise (positive)', 'Surprise (negative)']:
                reason = 'Unexpected twist'
            elif peak['emotion'] in ['Contemplation', 'Realization']:
                reason = 'Insightful observation'
            else:
                reason = f"Strong {peak['emotion']} moment"

            candidates.append((start, end, reason))

        # Add vocal burst locations
        vocal_bursts = hume_data.get('vocal_burst', {})
        for burst in vocal_bursts.get('segments', []):
            time = burst.get('time', {}).get('begin', 0)
            candidates.append(
                (max(0, time - 1), time + 1, 'Non-verbal expression')
            )

        # Sort by time
        candidates.sort(key=lambda x: x[0])

        # Merge overlapping windows
        merged = []
        for start, end, reason in candidates:
            if merged and start <= merged[-1][1]:
                # Overlap, extend the window
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]),
                            merged[-1][2] + f' + {reason}')
            else:
                merged.append((start, end, reason))

        return merged[:7]  # Return top 7 candidate regions


# Utility functions for direct use

def process_hume_data(hume_json_str: str, strategy: str = 'peaks') -> Dict[str, Any]:
    """
    Main entry point for processing Hume data.

    Args:
        hume_json_str: JSON string of Hume data
        strategy: Processing strategy

    Returns:
        Compressed emotional summary
    """
    try:
        hume_data = json.loads(hume_json_str)
    except json.JSONDecodeError:
        return {'error': 'Invalid JSON data'}

    processor = HumeProcessor()
    return processor.create_emotional_summary(hume_data, strategy=strategy)


def get_emotional_context(hume_json_str: str) -> str:
    """
    Get a formatted emotional context string for LLM prompts.

    Args:
        hume_json_str: JSON string of Hume data

    Returns:
        Formatted string (< 100 tokens)
    """
    summary = process_hume_data(hume_json_str, strategy='full_summary')
    return HumeProcessor.format_for_prompt(summary)