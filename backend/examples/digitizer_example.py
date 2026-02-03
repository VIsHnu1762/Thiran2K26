"""
BillAgent Pro - DigitizerAgent Usage Example
=============================================
Demonstrates how to use the new OCR service architecture.
"""

import asyncio
import os
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agents.digitizer import DigitizerAgent, create_digitizer_agent
from backend.app.services.ocr import MistralOCR, GPT4VisionOCR


async def basic_extraction_example():
    """
    Basic example: Extract data from a bill image.
    """
    print("=" * 60)
    print("Example 1: Basic Bill Extraction")
    print("=" * 60)
    
    # Create digitizer agent (uses settings from environment)
    agent = create_digitizer_agent()
    
    # Check health of OCR engines
    health = await agent.health_check()
    print(f"\nOCR Engine Health:")
    print(f"  Primary: {health['primary']}")
    print(f"  Fallback: {health['fallback']}")
    
    # Load sample image
    sample_image_path = Path(__file__).parent / "samples" / "bill_sample.jpg"
    
    if not sample_image_path.exists():
        print(f"\n⚠️  Sample image not found: {sample_image_path}")
        print("   Please add a sample bill image to test extraction.")
        return
    
    with open(sample_image_path, "rb") as f:
        image_bytes = f.read()
    
    # Extract data from image
    print("\n📄 Processing bill image...")
    result = await agent.extract(
        image_bytes=image_bytes,
        image_url=str(sample_image_path),
    )
    
    # Display results
    print(f"\n✅ Extraction Status: {result.status.value}")
    print(f"   Processing Time: {result.total_processing_time_ms}ms")
    print(f"   Primary Engine Used: {result.primary_engine_used}")
    
    if result.fallback_reason:
        print(f"   Fallback Reason: {result.fallback_reason}")
    
    if result.ocr_result:
        ocr = result.ocr_result
        print(f"\n📊 Extracted Data:")
        print(f"   Overall Confidence: {ocr.overall_confidence:.1%}")
        
        if ocr.vendor_name:
            print(f"   Vendor: {ocr.vendor_name.value} ({ocr.vendor_name.confidence:.1%})")
        
        if ocr.invoice_number:
            print(f"   Invoice #: {ocr.invoice_number.value}")
        
        if ocr.invoice_date:
            print(f"   Date: {ocr.invoice_date.value}")
        
        if ocr.total_amount:
            print(f"   Total: {ocr.total_amount.value}")
        
        print(f"\n   Line Items ({len(ocr.line_items)}):")
        for item in ocr.line_items:
            print(f"     - {item.description}: {item.quantity} × {item.unit_price} = {item.total_price}")
        
        # Show bounding boxes
        if ocr.bounding_boxes:
            print(f"\n   Bounding Boxes: {len(ocr.bounding_boxes)} fields detected")
    
    if result.validation_errors:
        print(f"\n⚠️  Validation Issues:")
        for error in result.validation_errors:
            print(f"   [{error['severity']}] {error['field']}: {error['message']}")
    
    print(f"\n   Suggested Status: {result.suggested_status}")
    
    # Cleanup
    await agent.close()


async def custom_engines_example():
    """
    Example: Using custom OCR engine configuration.
    """
    print("\n" + "=" * 60)
    print("Example 2: Custom Engine Configuration")
    print("=" * 60)
    
    # Get API keys from environment
    mistral_key = os.getenv("MISTRAL_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not mistral_key:
        print("\n⚠️  MISTRAL_API_KEY not set, skipping custom engine example")
        return
    
    # Create custom OCR engines
    primary = MistralOCR(
        api_key=mistral_key,
        model="pixtral-large-latest",
        timeout=120.0,
    )
    
    fallback = None
    if openai_key:
        fallback = GPT4VisionOCR(
            api_key=openai_key,
            model="gpt-4o",
        )
    
    # Create agent with custom engines
    agent = DigitizerAgent(
        primary_ocr=primary,
        fallback_ocr=fallback,
        max_retries=3,
        confidence_threshold=0.8,
    )
    
    print(f"\n✅ Agent created with custom configuration")
    print(f"   Primary Engine: {primary.engine_type.value}")
    print(f"   Fallback Engine: {fallback.engine_type.value if fallback else 'None'}")
    print(f"   Confidence Threshold: 0.8")
    
    await agent.close()


async def batch_processing_example():
    """
    Example: Process multiple bills in batch.
    """
    print("\n" + "=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)
    
    agent = create_digitizer_agent()
    
    # Sample directory with multiple bills
    samples_dir = Path(__file__).parent / "samples"
    
    if not samples_dir.exists():
        print(f"\n⚠️  Samples directory not found: {samples_dir}")
        return
    
    # Find all image files
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    image_files = [
        f for f in samples_dir.iterdir()
        if f.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"\n⚠️  No image files found in {samples_dir}")
        return
    
    print(f"\n📁 Found {len(image_files)} bill images")
    
    results = []
    for image_path in image_files:
        print(f"\n   Processing: {image_path.name}...", end=" ")
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        result = await agent.extract(
            image_bytes=image_bytes,
            image_url=str(image_path),
        )
        
        results.append({
            "file": image_path.name,
            "status": result.status.value,
            "confidence": result.ocr_result.overall_confidence if result.ocr_result else 0,
            "items": len(result.ocr_result.line_items) if result.ocr_result else 0,
            "time_ms": result.total_processing_time_ms,
        })
        
        print(f"{result.status.value} ({result.total_processing_time_ms}ms)")
    
    # Summary
    print(f"\n📊 Batch Processing Summary:")
    print(f"   Total Files: {len(results)}")
    
    successful = [r for r in results if r["status"] == "success"]
    partial = [r for r in results if r["status"] == "partial"]
    failed = [r for r in results if r["status"] == "failed"]
    
    print(f"   Successful: {len(successful)}")
    print(f"   Partial: {len(partial)}")
    print(f"   Failed: {len(failed)}")
    
    if results:
        avg_confidence = sum(r["confidence"] for r in results) / len(results)
        avg_time = sum(r["time_ms"] for r in results) / len(results)
        total_items = sum(r["items"] for r in results)
        
        print(f"   Avg Confidence: {avg_confidence:.1%}")
        print(f"   Avg Time: {avg_time:.0f}ms")
        print(f"   Total Items Extracted: {total_items}")
    
    await agent.close()


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("BillAgent Pro - DigitizerAgent Examples")
    print("=" * 60)
    
    await basic_extraction_example()
    await custom_engines_example()
    await batch_processing_example()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
